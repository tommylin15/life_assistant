import 'package:flutter/material.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import 'browser_navigation.dart';
import 'note_api.dart';
import 'note_drive_relations.dart';
import 'visual_system.dart';

final _notesProvider = FutureProvider.family<_Workspace, String>((ref, query) async {
  final api = ref.read(noteApiProvider);
  final values = await Future.wait([api.getNotes(query: query), api.getProjects()]);
  return _Workspace(
    notes: values[0].map(_Note.fromJson).toList(),
    projects: values[1].map(_Project.fromJson).toList(),
  );
});

class NotesPage extends ConsumerStatefulWidget {
  const NotesPage({super.key});

  @override
  ConsumerState<NotesPage> createState() => _NotesPageState();
}

class _NotesPageState extends ConsumerState<NotesPage> {
  final _search = TextEditingController();
  String _query = '';
  String? _categoryFilter; // null: all, empty: uncategorized

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  void _reload() => ref.invalidate(_notesProvider(_query));

  @override
  Widget build(BuildContext context) {
    final value = ref.watch(_notesProvider(_query));
    final workspace = value.asData?.value;
    final wide = MediaQuery.sizeOf(context).width >= 720;
    return Scaffold(
      appBar: AppBar(
        title: const Text('筆記'),
        actions: [
          IconButton(
            key: const ValueKey('note-categories-open'),
            tooltip: '筆記分類',
            icon: const Icon(Icons.folder_open_outlined),
            onPressed: workspace == null ? null : () => showModalBottomSheet<void>(
              context: context,
              builder: (sheet) => SafeArea(
                child: SizedBox(height: 400,
                  child: _categoryMenu(workspace, closeOnTap: sheet)),
              ),
            ),
          ),
          if (wide)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: FilledButton.icon(
                onPressed: workspace == null ? null : () => _edit(workspace),
                icon: const Icon(Icons.note_add_outlined),
                label: const Text('新增筆記'),
              ),
            ),
        ],
      ),
      body: value.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _ErrorState(error: error, onRetry: _reload),
        data: _content,
      ),
      floatingActionButton: !wide && workspace != null
          ? FloatingActionButton(
              tooltip: '新增筆記',
              onPressed: () => _edit(workspace),
              child: const Icon(Icons.note_add_outlined),
            )
          : null,
    );
  }

  Widget _content(_Workspace workspace) {
    final shown = workspace.notes.where((note) => _categoryFilter == null ||
        (note.category ?? '') == _categoryFilter).toList();
    return Row(children: [
      if (MediaQuery.sizeOf(context).width >= 900)
        SizedBox(width: 192, child: _categoryMenu(workspace)),
      Expanded(child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1040),
          child: CustomScrollView(
            slivers: [
              const SliverPadding(
                padding: EdgeInsets.fromLTRB(16, 16, 16, 0),
                sliver: SliverToBoxAdapter(child: LifeFeatureHeader(feature: LifeVisualFeature.notes)),
              ),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                sliver: SliverToBoxAdapter(child: Card(
                  color: Theme.of(context).colorScheme.primary.withValues(alpha: .07),
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Row(children: [
                      const Icon(Icons.lightbulb_outline, size: 28),
                      const SizedBox(width: 12),
                      const Expanded(child: Text('想到什麼，就先記下來。')),
                      OutlinedButton.icon(
                        onPressed: () => _edit(workspace),
                        icon: const Icon(Icons.edit_note),
                        label: const Text('隨手寫')),
                    ]),
                  ),
                )),
              ),
              SliverPadding(
                padding: const EdgeInsets.all(16),
                sliver: SliverToBoxAdapter(
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          key: const ValueKey('notes-search-field'),
                          controller: _search,
                          textInputAction: TextInputAction.search,
                          decoration: const InputDecoration(
                            prefixIcon: Icon(Icons.search),
                            hintText: '搜尋筆記標題或內容',
                          ),
                          onSubmitted: (_) => _applySearch(),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton.filledTonal(
                        key: const ValueKey('notes-search-button'),
                        tooltip: '搜尋',
                        onPressed: _applySearch,
                        icon: const Icon(Icons.search),
                      ),
                    ],
                  ),
                ),
              ),
              if (_query.isNotEmpty)
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                  sliver: SliverToBoxAdapter(
                    child: Text('搜尋「$_query」：${shown.length} 筆'),
                  ),
                ),
              if (shown.isEmpty)
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: Center(
                    child: Text(_categoryFilter != null ? '此分類目前沒有符合的筆記' :
                        _query.isEmpty ? '還沒有筆記' : '找不到符合的筆記'),
                  ),
                )
              else
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 96),
                  sliver: SliverList.builder(
                    itemCount: shown.length,
                    itemBuilder: (_, index) {
                      final note = shown[index];
                      return Card(
                        color: Color.lerp(Theme.of(context).colorScheme.surface,
                          const Color(0xFFBE9468), index.isEven ? .075 : .035),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            ListTile(
                              onTap: () => _edit(workspace, note: note),
                              leading: Container(
                                width: 42, height: 42,
                                decoration: BoxDecoration(
                                  color: Theme.of(context).colorScheme.primary.withValues(alpha: .09),
                                  borderRadius: BorderRadius.circular(13)),
                                child: const Icon(Icons.sticky_note_2_outlined)),
                              title: Text(note.displayTitle),
                              subtitle: Text(
                                [
                                  if (note.body.trim().isNotEmpty) _plain(note.body),
                                  if (workspace.projectName(note.projectId) case final name?) name,
                                  note.category ?? '未分類',
                                  if (note.updatedAt case final updated?)
                                    '更新 ${DateFormat('M/d HH:mm').format(updated.toLocal())}',
                                ].join('\n'),
                                maxLines: 4,
                                overflow: TextOverflow.ellipsis,
                              ),
                              trailing: PopupMenuButton<String>(
                                tooltip: '筆記選項',
                                onSelected: (action) {
                                  if (action == 'edit') _edit(workspace, note: note);
                                  if (action == 'category') _quickCategory(workspace, note);
                                  if (action == 'links') _links(workspace, note);
                                  if (action == 'delete') _delete(note);
                                },
                                itemBuilder: (_) => const [
                                  PopupMenuItem(value: 'edit', child: Text('編輯')),
                                  PopupMenuItem(value: 'category', child: Text('變更分類')),
                                  PopupMenuItem(value: 'links', child: Text('雙向連結')),
                                  PopupMenuItem(value: 'delete', child: Text('刪除')),
                                ],
                              ),
                            ),
                            for (final link in noteUrls(note.body).take(2))
                              Align(
                                alignment: Alignment.centerLeft,
                                child: TextButton.icon(
                                  icon: const Icon(Icons.open_in_new, size: 16),
                                  label: Text(link, overflow: TextOverflow.ellipsis),
                                  onPressed: () => ref.read(browserNavigationProvider).openExternal(link),
                                ),
                              ),
                            NoteDriveRelations(noteId: note.id),
                          ],
                        ),
                      );
                    },
                  ),
                ),
            ],
          ),
        ),
      )),
    ]);
  }

  Widget _categoryMenu(_Workspace workspace, {BuildContext? closeOnTap}) {
    final categories = workspace.notes.map((note) => note.category)
        .whereType<String>().toSet().toList()..sort();
    void choose(String? category) {
      setState(() => _categoryFilter = category);
      if (closeOnTap != null) Navigator.of(closeOnTap).pop();
    }
    return ListView(children: [
      const ListTile(title: Text('筆記分類')),
      ListTile(
        key: const ValueKey('note-category-all'),
        leading: const Icon(Icons.all_inbox_outlined),
        title: const Text('全部筆記'),
        selected: _categoryFilter == null,
        onTap: () => choose(null),
      ),
      ListTile(
        key: const ValueKey('note-category-uncategorized'),
        leading: const Icon(Icons.folder_off_outlined),
        title: const Text('未分類'),
        selected: _categoryFilter == '',
        onTap: () => choose(''),
      ),
      for (final category in categories)
        ListTile(
          key: ValueKey('note-category-$category'),
          leading: const Icon(Icons.folder_outlined),
          title: Text(category),
          selected: _categoryFilter == category,
          onTap: () => choose(category),
        ),
    ]);
  }

  void _applySearch() => setState(() => _query = _search.text.trim());

  Future<void> _edit(_Workspace workspace, {_Note? note}) async {
    final api = ref.read(noteApiProvider);
    List<String> tags = const [];
    if (note != null) {
      try {
        tags = await api.getNoteTags(note.id);
      } catch (error) {
        if (mounted) _message('載入標籤失敗：$error');
      }
    }
    if (!mounted) return;
    final result = await showDialog<_EditorResult>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _EditorDialog(
        note: note,
        projects: workspace.projects,
        initialTags: tags,
      ),
    );
    if (result == null || !mounted) return;

    try {
      final saved = note == null
          ? await api.createNote(result.body)
          : await api.updateNote(note.id, result.body);
      final id = saved['id']?.toString() ?? note?.id;
      if (id == null) throw StateError('Note response did not contain an id');
      Object? tagError;
      try {
        await api.replaceNoteTags(id, result.tags);
      } catch (error) {
        tagError = error;
      }
      _reload();
      if (!mounted) return;
      _message(tagError == null
          ? (note == null ? '筆記已新增' : '筆記已更新')
          : '筆記已儲存，但標籤更新失敗：$tagError');
    } catch (error) {
      _message('操作失敗：$error');
    }
  }


  Future<void> _quickCategory(_Workspace workspace, _Note note) async {
    final categories = workspace.notes.map((item) => item.category)
        .whereType<String>().toSet().toList()..sort();
    final chosen = await showDialog<String>(
      context: context,
      builder: (dialog) => SimpleDialog(
        title: Text('變更分類 · ${note.displayTitle}'),
        children: [
          SimpleDialogOption(
            onPressed: () => Navigator.pop(dialog, ''),
            child: const Text('未分類'),
          ),
          for (final category in categories)
            SimpleDialogOption(
              onPressed: () => Navigator.pop(dialog, category),
              child: Text(category),
            ),
          SimpleDialogOption(
            onPressed: () => Navigator.pop(dialog, '__new_category__'),
            child: const Text('＋ 新增分類'),
          ),
        ],
      ),
    );
    if (chosen == null || !mounted) return;
    var category = chosen;
    if (category == '__new_category__') {
      final input = TextEditingController();
      final custom = await showDialog<String>(
        context: context,
        builder: (dialog) => AlertDialog(
          title: const Text('新增分類'),
          content: TextField(
            key: const ValueKey('note-new-category-field'),
            controller: input,
            maxLength: 80,
            decoration: const InputDecoration(hintText: '分類名稱'),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialog),
                child: const Text('取消')),
            FilledButton(onPressed: () => Navigator.pop(dialog, input.text.trim()),
                child: const Text('確定')),
          ],
        ),
      );
      input.dispose();
      if (custom == null || !mounted) return;
      category = custom;
    }
    try {
      await ref.read(noteApiProvider).updateNote(note.id,
          {'category': category.isEmpty ? null : category});
      _reload();
      if (mounted) _message('分類已更新');
    } catch (error) {
      _message('更新分類失敗：$error');
    }
  }

  Future<void> _links(_Workspace workspace, _Note note) async {
    await showDialog<void>(
      context: context,
      builder: (_) => _LinksDialog(note: note, notes: workspace.notes),
    );
  }

  Future<void> _delete(_Note note) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('刪除筆記？'),
        content: Text('確定要刪除「${note.displayTitle}」？這個動作需要明確確認。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('刪除'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    try {
      await ref.read(noteApiProvider).deleteNote(note.id);
      _reload();
      if (mounted) _message('筆記已刪除');
    } catch (error) {
      _message('操作失敗：$error');
    }
  }

  void _message(String text) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
    }
  }

  static String _plain(String value) => value
      .replaceAll(RegExp(r'[#>*_`~\[\]\(\)-]+'), ' ')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();
}

class _EditorDialog extends StatefulWidget {
  const _EditorDialog({
    required this.note,
    required this.projects,
    required this.initialTags,
  });
  final _Note? note;
  final List<_Project> projects;
  final List<String> initialTags;

  @override
  State<_EditorDialog> createState() => _EditorDialogState();
}

class _EditorDialogState extends State<_EditorDialog> {
  final _form = GlobalKey<FormState>();
  late final TextEditingController _title;
  late final TextEditingController _body;
  late final TextEditingController _tags;
  late final TextEditingController _category;
  String? _projectId;
  bool _preview = false;

  @override
  void initState() {
    super.initState();
    _title = TextEditingController(text: widget.note?.title ?? '');
    _body = TextEditingController(text: widget.note?.body ?? '');
    _tags = TextEditingController(text: widget.initialTags.join(', '));
    _category = TextEditingController(text: widget.note?.category ?? '');
    _projectId = widget.note?.projectId;
  }

  @override
  void dispose() {
    _title.dispose();
    _body.dispose();
    _tags.dispose();
    _category.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final compact = MediaQuery.sizeOf(context).width < 600;
    return AlertDialog(
      insetPadding: EdgeInsets.all(compact ? 12 : 32),
      title: Text(widget.note == null ? '新增筆記' : '編輯筆記'),
      content: SizedBox(
        width: compact ? double.maxFinite : 720,
        height: compact ? MediaQuery.sizeOf(context).height * .72 : 580,
        child: Column(
          children: [
            SegmentedButton<bool>(
              segments: const [
                ButtonSegment(
                  value: false,
                  label: Text('編輯'),
                  icon: Icon(Icons.edit_outlined),
                ),
                ButtonSegment(
                  value: true,
                  label: Text('預覽'),
                  icon: Icon(Icons.visibility_outlined),
                ),
              ],
              selected: {_preview},
              onSelectionChanged: (values) =>
                  setState(() => _preview = values.first),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: _preview
                  ? SingleChildScrollView(
                      key: const ValueKey('note-markdown-preview'),
                      child: MarkdownBody(
                        data: _body.text.isEmpty ? '_目前沒有內容_' : _body.text,
                        onTapLink: (text, href, title) {
                          final uri = href == null ? null : Uri.tryParse(href);
                          if (uri != null && (uri.scheme == 'https' || uri.scheme == 'http') && uri.host.isNotEmpty) {
                            openExternalBrowser(href!);
                          }
                        },
                      ),
                    )
                  : Form(
                      key: _form,
                      child: SingleChildScrollView(
                        child: Column(
                          children: [
                            TextFormField(
                              key: const ValueKey('note-title-field'),
                              controller: _title,
                              decoration: const InputDecoration(labelText: '標題（可留白，自動產生）'),
                            ),
                            const SizedBox(height: 12),
                            DropdownButtonFormField<String>(
                              key: const ValueKey('note-project-field'),
                              initialValue: _projectId ?? '',
                              decoration: const InputDecoration(labelText: '專案'),
                              items: [
                                const DropdownMenuItem(
                                  value: '',
                                  child: Text('不指定專案'),
                                ),
                                for (final project in widget.projects)
                                  DropdownMenuItem(
                                    value: project.id,
                                    child: Text(project.name),
                                  ),
                              ],
                              onChanged: (value) => _projectId =
                                  value == null || value.isEmpty ? null : value,
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              key: const ValueKey('note-category-field'),
                              controller: _category,
                              maxLength: 80,
                              decoration: const InputDecoration(
                                labelText: '分類', hintText: '未分類／輸入名稱建立新分類'),
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              key: const ValueKey('note-tags-field'),
                              controller: _tags,
                              decoration: const InputDecoration(
                                labelText: '標籤',
                                hintText: '用逗號分隔',
                              ),
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              key: const ValueKey('note-body-field'),
                              controller: _body,
                              minLines: compact ? 10 : 14,
                              maxLines: null,
                              decoration: const InputDecoration(
                                labelText: 'Markdown 內容',
                                alignLabelWithHint: true,
                              ),
                              onChanged: (_) => setState(() {}),
                            ),
                          ],
                        ),
                      ),
                    ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('取消'),
        ),
        FilledButton(
          key: const ValueKey('note-save-button'),
          onPressed: _save,
          child: const Text('儲存'),
        ),
      ],
    );
  }

  void _save() {
    if (!_preview && !(_form.currentState?.validate() ?? false)) return;
    final tags = <String>[];
    final seen = <String>{};
    for (final raw in _tags.text.split(',')) {
      final tag = raw.trim();
      if (tag.isNotEmpty && seen.add(tag.toLowerCase())) tags.add(tag);
    }
    Navigator.pop(
      context,
      _EditorResult(
        body: {
          'title': _title.text.trim().isEmpty
              ? suggestedNoteTitle(_body.text) : _title.text.trim(),
          'body': _body.text,
          'project_id': _projectId,
          'category': _category.text.trim().isEmpty ? null : _category.text.trim(),
        },
        tags: tags,
      ),
    );
  }
}

class _LinksDialog extends ConsumerStatefulWidget {
  const _LinksDialog({required this.note, required this.notes});
  final _Note note;
  final List<_Note> notes;

  @override
  ConsumerState<_LinksDialog> createState() => _LinksDialogState();
}

class _LinksDialogState extends ConsumerState<_LinksDialog> {
  List<_Note>? _links;
  String? _targetId;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final raw = await ref.read(noteApiProvider).getNoteLinks(widget.note.id);
      if (mounted) setState(() => _links = raw.map(_Note.fromJson).toList());
    } catch (error) {
      if (mounted) setState(() => _error = error);
    }
  }

  @override
  Widget build(BuildContext context) {
    final links = _links;
    final linkedIds = links?.map((note) => note.id).toSet() ?? <String>{};
    final targets = widget.notes
        .where((note) => note.id != widget.note.id && !linkedIds.contains(note.id))
        .toList();
    return AlertDialog(
      title: Text('雙向連結 · ${widget.note.displayTitle}'),
      content: SizedBox(
        width: 520,
        child: _error != null
            ? Text('載入連結失敗：$_error')
            : links == null
                ? const LinearProgressIndicator()
                : Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (links.isEmpty) const Text('尚未連結其他筆記'),
                      for (final linked in links)
                        ListTile(
                          title: Text(linked.displayTitle),
                          trailing: IconButton(
                            tooltip: '移除與 ${linked.displayTitle} 的連結',
                            onPressed: () => _unlink(linked.id),
                            icon: const Icon(Icons.link_off),
                          ),
                        ),
                      if (targets.isNotEmpty) ...[
                        const Divider(),
                        DropdownButtonFormField<String>(
                          key: const ValueKey('note-link-target-field'),
                          initialValue: _targetId,
                          decoration:
                              const InputDecoration(labelText: '連結另一則筆記'),
                          items: [
                            for (final target in targets)
                              DropdownMenuItem(
                                value: target.id,
                                child: Text(target.displayTitle),
                              ),
                          ],
                          onChanged: (value) =>
                              setState(() => _targetId = value),
                        ),
                        const SizedBox(height: 8),
                        Align(
                          alignment: Alignment.centerRight,
                          child: FilledButton.icon(
                            key: const ValueKey('note-link-add-button'),
                            onPressed: _targetId == null ? null : _link,
                            icon: const Icon(Icons.add_link),
                            label: const Text('新增雙向連結'),
                          ),
                        ),
                      ],
                    ],
                  ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('關閉'),
        ),
      ],
    );
  }

  Future<void> _link() async {
    final target = _targetId;
    if (target == null) return;
    try {
      await ref.read(noteApiProvider).linkNote(widget.note.id, target);
      _targetId = null;
      await _load();
    } catch (error) {
      if (mounted) setState(() => _error = error);
    }
  }

  Future<void> _unlink(String target) async {
    try {
      await ref.read(noteApiProvider).unlinkNote(widget.note.id, target);
      await _load();
    } catch (error) {
      if (mounted) setState(() => _error = error);
    }
  }
}

class _Workspace {
  const _Workspace({required this.notes, required this.projects});
  final List<_Note> notes;
  final List<_Project> projects;

  String? projectName(String? id) {
    if (id == null) return null;
    for (final project in projects) {
      if (project.id == id) return project.name;
    }
    return '未知專案';
  }
}

class _Note {
  const _Note({
    required this.id,
    required this.title,
    required this.body,
    required this.projectId,
    required this.category,
    required this.updatedAt,
  });
  factory _Note.fromJson(Map<String, dynamic> json) => _Note(
        id: json['id'].toString(),
        title: json['title']?.toString(),
        body: json['body']?.toString() ?? '',
        projectId: json['project_id']?.toString(),
        category: json['category']?.toString(),
        updatedAt: DateTime.tryParse(json['updated_at']?.toString() ?? ''),
      );
  final String id;
  final String? title;
  final String body;
  final String? projectId;
  final String? category;
  final DateTime? updatedAt;
  String get displayTitle =>
      (title?.trim().isNotEmpty ?? false) ? title!.trim() : suggestedNoteTitle(body);
}

class _Project {
  const _Project({required this.id, required this.name});
  factory _Project.fromJson(Map<String, dynamic> json) => _Project(
        id: json['id'].toString(),
        name: json['name']?.toString() ?? '未命名專案',
      );
  final String id;
  final String name;
}

class _EditorResult {
  const _EditorResult({required this.body, required this.tags});
  final Map<String, dynamic> body;
  final List<String> tags;
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.error, required this.onRetry});
  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('筆記載入失敗'),
            const SizedBox(height: 8),
            Text('$error', maxLines: 3, overflow: TextOverflow.ellipsis),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('重試'),
            ),
          ],
        ),
      );
}

String suggestedNoteTitle(String body) {
  final cleaned = body.replaceAll(RegExp(r'(?m)^\s{0,3}(?:#{1,6}|[-*>])\s*'), '')
      .replaceAll(RegExp(r'[*_~\[\]]'), '')
      .replaceAll(String.fromCharCode(96), '').trim()
      .replaceAll(RegExp(r'\s+'), ' ');
  final sentence = cleaned.split(RegExp(r'[。！？.!?]')).first.trim();
  if (sentence.isEmpty) return '未命名筆記';
  return sentence.runes.length <= 30 ? sentence :
      String.fromCharCodes(sentence.runes.take(10));
}

Iterable<String> noteUrls(String body) =>
    RegExp(r'https?://[^\s<>\]\)]+', caseSensitive: false)
        .allMatches(body)
        .map((match) => match.group(0)!
            .replaceFirst(RegExp(r'[.,;:!?。！，；：]+$'), ''))
        .where((link) => Uri.tryParse(link)?.host.isNotEmpty == true)
        .toSet();
