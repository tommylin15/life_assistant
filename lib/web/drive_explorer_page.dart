import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'browser_navigation.dart';
import 'drive_api.dart';
import 'google_drive_picker.dart';
import 'platform_api.dart';

/// Google Drive explorer for files *created/opened by this application*.
/// This intentionally does not claim that drive.file grants entire-Drive access.
class DriveExplorerPage extends ConsumerStatefulWidget {
  const DriveExplorerPage({super.key});

  @override
  ConsumerState<DriveExplorerPage> createState() => _DriveExplorerPageState();
}

class _DriveExplorerPageState extends ConsumerState<DriveExplorerPage> {
  List<Map<String, dynamic>> _files = const [];
  List<({String id, String name})> _path = const [];
  bool _loading = true;
  bool _working = false;
  bool _selecting = false;
  String? _error;
  String? _nextPageToken;
  String _query = '';
  final TextEditingController _search = TextEditingController();

  String? get _folderId => _path.isEmpty ? null : _path.last.id;

  @override
  void initState() {
    super.initState();
    _read();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  String _apiPath({String? token}) {
    final query = <String, String>{'page_size': '50'};
    if (_folderId != null) query['folder_id'] = _folderId!;
    if (_query.isNotEmpty) query['q'] = _query;
    if (token != null) query['page_token'] = token;
    return '/drive/manager/files?' + Uri(queryParameters: query).query;
  }

  Future<void> _read({String? token}) async {
    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await ref.read(platformApiProvider).get(_apiPath(token: token));
      if (!mounted) return;
      setState(() {
        _files = (data['files'] as List? ?? const [])
            .map((x) => Map<String, dynamic>.from(x as Map)).toList();
        _nextPageToken = data['next_page_token']?.toString();
        if (data['incomplete_search'] == true) {
          _error = 'Google Drive 回報搜尋結果可能不完整，請縮小搜尋條件。';
        }
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          _files = [];
          _nextPageToken = null;
          _error = '無法讀取已授權的 Drive 檔案。請檢查 Google 連線或重新授權。';
        });
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _enterFolder(Map<String, dynamic> folder) {
    final id = folder['id']?.toString() ?? '';
    if (id.isEmpty) return;
    setState(() {
      _path = [..._path, (id: id, name: folder['name']?.toString() ?? '資料夾')];
      _query = '';
      _search.clear();
    });
    _read();
  }

  void _goToIndex(int index) {
    setState(() {
      _path = index < 0 ? [] : _path.sublist(0, index + 1);
      _query = '';
      _search.clear();
    });
    _read();
  }

  bool _safeGoogleUrl(String? url) {
    final parsed = Uri.tryParse(url ?? '');
    return parsed != null && parsed.scheme == 'https' &&
        const {
          'drive.google.com', 'docs.google.com',
          'sheets.google.com', 'slides.google.com'
        }.contains(parsed.host);
  }

  void _open(Map<String, dynamic> file) {
    final url = file['web_view_link']?.toString();
    if (!_safeGoogleUrl(url)) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text('Google 沒有提供可驗證的原檔網址，請從 Google Drive 開啟。'),
      ));
      return;
    }
    openExternalBrowser(url!);
  }

  bool _canPreviewText(Map<String, dynamic> file) =>
      const {'text/plain', 'text/markdown', 'text/csv', 'application/json'}
          .contains(file['mime_type']);

  Future<void> _previewText(Map<String, dynamic> file, {bool edit = false}) async {
    final id = file['id']?.toString() ?? '';
    if (id.isEmpty || !_canPreviewText(file)) return;
    if (edit && (file['can_edit'] != true || _working)) return;
    try {
      final result = await ref.read(platformApiProvider).get(
        '/drive/manager/files/' + Uri.encodeComponent(id) + '/text-preview');
      if (!mounted) return;
      final originalText = result['text']?.toString() ?? '';
      final canSave = edit && result['can_edit'] == true &&
          (result['version']?.toString() ?? '').isNotEmpty &&
          (result['content_sha256']?.toString() ?? '').isNotEmpty;
      if (edit && !canSave) {
        setState(() => _error = '缺少 Drive 寫入權限或文件版本，無法安全編輯；請使用 Google 原檔。');
        return;
      }
      var draft = originalText;
      final submitted = await showDialog<String>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text((edit ? '編輯：' : '文字預覽：') +
              (result['name']?.toString() ?? '檔案')),
          content: SizedBox(
            width: 540,
            height: 380,
            child: edit
                ? TextFormField(
                    key: const ValueKey('drive-explorer-text-editor'),
                    initialValue: originalText,
                    expands: true,
                    maxLines: null,
                    minLines: null,
                    keyboardType: TextInputType.multiline,
                    onChanged: (value) => draft = value,
                    decoration: const InputDecoration(
                      border: OutlineInputBorder(),
                      helperText: '限 64KiB UTF-8，儲存前再次檢查原檔版本',
                    ),
                  )
                : SingleChildScrollView(
                    child: SelectableText(originalText),
                  ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx),
                child: Text(edit ? '取消' : '關閉')),
            if (edit)
              FilledButton(
                key: const ValueKey('drive-explorer-text-save'),
                onPressed: () => Navigator.pop(ctx, draft),
                child: const Text('儲存回 Google Drive'),
              ),
          ],
        ),
      );
      if (!edit || submitted == null || submitted == originalText || !mounted) {
        return;
      }
      setState(() => _working = true);
      try {
        final pickerApi = ref.read(drivePickerApiProvider);
        final docs = await pickerApi.registerDocuments([id]);
        if (docs.isEmpty) throw StateError('Unable to register Drive file');
        final documentId = docs.first['id']?.toString() ?? '';
        if (documentId.isEmpty) throw StateError('Missing registered document');
        final resultSave = await ref.read(platformApiProvider).put(
          '/drive/manager/documents/' +
              Uri.encodeComponent(documentId) + '/text',
          {
            'text': submitted,
            'expected_version': result['version']?.toString() ?? '',
            'expected_sha256': result['content_sha256']?.toString() ?? '',
          },
        );
        if (resultSave['verified'] != true) {
          throw StateError('Drive readback not verified');
        }
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('文字已寫入 Google Drive，並完成來源讀回驗證。')),
        );
        await _read();
      } catch (_) {
        if (mounted) setState(() => _error =
          '文字修改未確認成功或原檔版本已變更，請先重新開啟原檔檢查；不會自動覆寫。');
      } finally {
        if (mounted) setState(() => _working = false);
      }
    } catch (_) {
      if (mounted) setState(() => _error =
          '無法安全開啟此檔案，請使用 Google Drive 原始檔案入口。');
    }
  }

  Future<void> _selectFromDrive({required bool folders}) async {
    if (_selecting || _working) return;
    setState(() => _selecting = true);
    try {
      // Picker lets the person browse their entire Google Drive. Only files
      // explicitly picked (or created by Life) become visible to Life's API.
      final api = ref.read(drivePickerApiProvider);
      final config = PickerConfig.fromJson(await api.getPickerConfig());
      final selected = await ref.read(googleDrivePickerProvider).pick(
        config, folders: folders, multiSelect: !folders,
      );
      if (selected.isEmpty) return;
      final registered = await api.registerDocuments(selected);
      if (registered.length != selected.length) {
        throw StateError('Selected Drive items were not all registered');
      }
      if (!mounted) return;
      // The landing view shows app-authorized files irrespective of their
      // parent path; prevent a newly picked file being hidden by an old query.
      setState(() {
        _path = [];
        _query = '';
        _search.clear();
      });
      await _read();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('已加入 ${registered.length} 個已授權' +
            (folders ? '資料夾' : '檔案') +
            '。資料夾內其他原有檔案仍需個別授權。'),
      ));
    } catch (_) {
      if (mounted) setState(() => _error =
        'Google Picker 選取或授權未完成。請確認 Google 連線及帳號後重試；原有檔案不受影響。');
    } finally {
      if (mounted) setState(() => _selecting = false);
    }
  }

  Future<void> _createFolder() async {
    if (_working) return;
    var enteredName = '';
    final name = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('建立 Google Drive 資料夾'),
        content: TextField(
          onChanged: (value) => enteredName = value,
          autofocus: true,
          maxLength: 200,
          decoration: const InputDecoration(labelText: '資料夾名稱'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx),
              child: const Text('取消')),
          FilledButton(onPressed: () => Navigator.pop(ctx, enteredName.trim()),
              child: const Text('建立')),
        ],
      ),
    );
    if (!mounted || name == null || name.isEmpty) return;
    setState(() => _working = true);
    try {
      final payload = <String, dynamic>{'name': name};
      if (_folderId != null) payload['parent_id'] = _folderId;
      await ref.read(platformApiProvider).post('/drive/manager/folders', payload);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('資料夾已在 Google Drive 建立並確認。')),
      );
      await _read();
    } catch (_) {
      if (mounted) setState(() => _error =
          '建立資料夾未確認成功，請先重新整理 Google Drive 再重試。');
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  Future<void> _rename(Map<String, dynamic> file) async {
    if (_working || _selecting || file['can_edit'] != true) return;
    final sourceId = file['id']?.toString() ?? '';
    final previousName = file['name']?.toString() ?? '';
    final version = file['modified_at']?.toString() ?? '';
    if (sourceId.isEmpty || previousName.isEmpty || version.isEmpty) {
      setState(() => _error = '無法取得修改版本；請先重新整理。');
      return;
    }
    var nextName = previousName;
    final chosen = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('重新命名 Google Drive 原檔'),
        content: TextFormField(
          key: const ValueKey('drive-explorer-rename-input'),
          initialValue: previousName,
          autofocus: true,
          maxLength: 500,
          onChanged: (v) => nextName = v.trim(),
          decoration: const InputDecoration(labelText: '新名稱'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx), child: const Text('取消')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, nextName),
            child: const Text('確認改名')),
        ],
      ),
    );
    if (!mounted || chosen == null || chosen.isEmpty ||
        chosen == previousName) return;
    setState(() => _working = true);
    try {
      final docs = await ref.read(drivePickerApiProvider)
          .registerDocuments([sourceId]);
      if (docs.length != 1) throw StateError('Drive registration mismatch');
      final docId = docs.first['id']?.toString() ?? '';
      if (docId.isEmpty) throw StateError('Missing registered ID');
      final result = await ref.read(platformApiProvider).patch(
        '/drive/manager/documents/' + Uri.encodeComponent(docId) + '/rename',
        {'name': chosen, 'expected_modified_at': version},
      );
      if (result['name'] != chosen) {
        throw StateError('Drive rename readback is incomplete');
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Google Drive 原檔已重新命名並確認。')));
      await _read();
    } catch (_) {
      if (mounted) setState(() => _error =
          '改名未確認成功，或 Google Drive 原檔已變更；請重新整理來源後再操作。');
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  Future<void> _move(Map<String, dynamic> file) async {
    if (_working || file['is_folder'] == true) return;
    final sourceId = file['id']?.toString() ?? '';
    final sourceVersion = file['modified_at']?.toString() ?? '';
    if (sourceId.isEmpty || sourceVersion.isEmpty) return;
    setState(() => _working = true);
    try {
      final pickerApi = ref.read(drivePickerApiProvider);
      final picker = PickerConfig.fromJson(await pickerApi.getPickerConfig());
      final targets = await ref.read(googleDrivePickerProvider)
          .pick(picker, folders: true, multiSelect: false);
      if (targets.isEmpty) return;
      if (!mounted) return;
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('確認移動原始檔案'),
          content: Text('將「' + (file['name']?.toString() ?? '未命名檔案') +
              '」移動到剛選取的 Google Drive 資料夾？'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false),
                child: const Text('取消')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true),
                child: const Text('確定移動')),
          ],
        ),
      );
      if (confirmed != true) return;
      // The existing picker-backed registration checks file access, and
      // the move API verifies document ownership again before Google write.
      final docs = await pickerApi.registerDocuments([sourceId]);
      if (docs.isEmpty) throw StateError('Drive document registration failed');
      final docId = docs.first['id']?.toString() ?? '';
      await ref.read(platformApiProvider).post(
        '/drive/manager/documents/' + Uri.encodeComponent(docId) + '/move',
        {'destination_folder_id': targets.first,
         'expected_modified_at': sourceVersion},
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('檔案已移動並從 Google Drive 讀回確認。')),
      );
      await _read();
    } catch (_) {
      if (mounted) setState(() => _error =
          '移動未確認成功；請先回 Google Drive 檢查檔案位置，不要連續重試。');
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  IconData _icon(Map<String, dynamic> file) {
    if (file['is_folder'] == true) return Icons.folder_outlined;
    final mime = file['mime_type']?.toString() ?? '';
    if (mime.contains('pdf')) return Icons.picture_as_pdf_outlined;
    if (mime.contains('image')) return Icons.image_outlined;
    if (mime.contains('spreadsheet')) return Icons.table_chart_outlined;
    return Icons.description_outlined;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: RefreshIndicator(
        onRefresh: _read,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          Wrap(spacing: 12, runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text('Google Drive 檔案總管',
                style: Theme.of(context).textTheme.headlineSmall),
              FilledButton.icon(
                key: const ValueKey('drive-explorer-select-files'),
                onPressed: _loading || _working || _selecting
                    ? null : () => _selectFromDrive(folders: false),
                icon: const Icon(Icons.add_to_drive_outlined),
                label: Text(_selecting ? '選取中' : '選取更多檔案')),
              OutlinedButton.icon(
                key: const ValueKey('drive-explorer-select-folder'),
                onPressed: _loading || _working || _selecting
                    ? null : () => _selectFromDrive(folders: true),
                icon: const Icon(Icons.folder_shared_outlined),
                label: const Text('選取資料夾')),
              OutlinedButton.icon(
                key: const ValueKey('drive-explorer-new-folder'),
                onPressed: _loading || _working || _selecting ? null : _createFolder,
                icon: const Icon(Icons.create_new_folder_outlined),
                label: const Text('新建資料夾')),
            ],
          ),
          const SizedBox(height: 8),
          const Text('目前採 Google drive.file 逐檔授權：只顯示你透過「選取更多檔案」'
              '選過，或由 Life 建立的檔案。選取資料夾不會自動開放其所有子檔案。'
              '要查看全部雲端硬碟，請使用 Google Drive 官方網站，並確認與 Life 連線的是同一個 Google 帳號。'),
          TextButton.icon(
            key: const ValueKey('drive-explorer-open-google-drive'),
            onPressed: () => openExternalBrowser('https://drive.google.com/drive/my-drive'),
            icon: const Icon(Icons.open_in_new),
            label: const Text('在 Google Drive 查看全部檔案'),
          ),
          const SizedBox(height: 12),
          Wrap(spacing: 4, crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              ActionChip(
                avatar: const Icon(Icons.folder_open, size: 18),
                label: const Text('Life 已授權'),
                onPressed: _loading ? null : () => _goToIndex(-1)),
              for (var i = 0; i < _path.length; i++)
                ActionChip(
                  label: Text(_path[i].name),
                  onPressed: _loading ? null : () => _goToIndex(i)),
            ]),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey('drive-explorer-search'),
            controller: _search,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              labelText: '搜尋目前範圍檔名',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: IconButton(
                onPressed: _loading ? null : () {
                  _query = _search.text.trim();
                  _read();
                },
                icon: const Icon(Icons.search)),
              border: const OutlineInputBorder()),
            onSubmitted: (text) { _query = text.trim(); _read(); },
          ),
          const SizedBox(height: 12),
          if (_working) const LinearProgressIndicator(),
          if (_error != null)
            Card(child: ListTile(
              leading: const Icon(Icons.info_outline),
              title: Text(_error!),
              trailing: IconButton(onPressed: () => _read(),
                icon: const Icon(Icons.refresh)))),
          if (_loading)
            const Center(child: Padding(
              padding: EdgeInsets.all(20), child: CircularProgressIndicator()))
          else if (_files.isEmpty)
            const Card(child: Padding(
              padding: EdgeInsets.all(18),
              child: Text('這裡尚無可存取的檔案。請按「選取更多檔案」使用 Google Picker，授權想在 Life 管理的檔案。')))
          else for (final file in _files)
            Card(key: ValueKey('drive-file-' + (file['id']?.toString() ?? '')),
              child: ListTile(
                leading: Icon(_icon(file)),
                title: Text(file['name']?.toString() ?? '未命名',
                  maxLines: 2, overflow: TextOverflow.ellipsis),
                subtitle: Text(file['is_folder'] == true
                  ? '資料夾' : (file['mime_type']?.toString() ?? '檔案'),
                  maxLines: 1),
                onTap: file['is_folder'] == true
                  ? () => _enterFolder(file) : () => _open(file),
                trailing: PopupMenuButton<String>(
                  key: ValueKey('drive-file-menu-' + (file['id']?.toString() ?? '')),
                  onSelected: (choice) {
                    if (choice == 'open') _open(file);
                    if (choice == 'enter') _enterFolder(file);
                    if (choice == 'preview') _previewText(file);
                    if (choice == 'edit') _previewText(file, edit: true);
                    if (choice == 'rename') _rename(file);
                    if (choice == 'move') _move(file);
                  },
                  itemBuilder: (ctx) => [
                    if (file['is_folder'] == true)
                      const PopupMenuItem(value: 'enter', child: Text('進入資料夾'))
                    else
                      const PopupMenuItem(value: 'open', child: Text('原檔開啟／預覽')),
                    if (_canPreviewText(file))
                      const PopupMenuItem(value: 'preview', child: Text('Life 內文字預覽')),
                    if (_canPreviewText(file) && file['can_edit'] == true)
                      const PopupMenuItem(value: 'edit', child: Text('在 Life 內編輯文字')),
                    if (file['can_edit'] == true)
                      const PopupMenuItem(value: 'rename', child: Text('重新命名')),
                    if (file['can_edit'] == true && file['is_folder'] != true)
                      const PopupMenuItem(value: 'move', child: Text('移動至資料夾')),
                  ],
                ),
              ),
            ),
          if (!_loading) Align(
            alignment: Alignment.centerRight,
            child: OutlinedButton(
              onPressed: _nextPageToken == null || _working
                ? null : () => _read(token: _nextPageToken),
              child: const Text('載入下一頁')),
          ),
          const SizedBox(height: 12),
          Text('結果為 Google Drive 即時查詢，不複製整個檔案資料庫；'
              '檔案異動有版本檢查及原站讀回。',
              style: Theme.of(context).textTheme.bodySmall),
        ]),
      ),
    );
  }
}
