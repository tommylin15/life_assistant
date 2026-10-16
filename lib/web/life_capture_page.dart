import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'platform_api.dart';
import 'shopping_api.dart';

/// Single, account-gated capture surface. Suggestions never persist until commit.
class LifeCapturePage extends ConsumerStatefulWidget {
  const LifeCapturePage({super.key});

  @override
  ConsumerState<LifeCapturePage> createState() => _LifeCapturePageState();
}

class _LifeCapturePageState extends ConsumerState<LifeCapturePage> {
  final _input = TextEditingController();
  bool _busy = false;
  String? _error;
  String? _classification;
  List<Map<String, dynamic>> _candidates = [];
  List<Map<String, dynamic>> _lists = [];
  List<Map<String, dynamic>> _receipts = [];

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  String _newActionId(int index) =>
      'life-inbox-' + DateTime.now().microsecondsSinceEpoch.toString() + '-' + index.toString();

  bool _isUrl(String text) {
    final uri = Uri.tryParse(text.trim());
    return uri != null &&
        (uri.scheme == 'https' || uri.scheme == 'http') &&
        uri.host.isNotEmpty &&
        !text.trim().contains(RegExp(r'\s'));
  }

  Future<void> _interpret() async {
    if (_busy || _input.text.trim().isEmpty) return;
    setState(() {
      _busy = true;
      _error = null;
      _receipts = [];
      _candidates = [];
    });
    try {
      final parsed = await ref.read(platformApiProvider).post('/inbox/interpret',
          {'text': _input.text.trim(), 'timezone': 'Asia/Taipei'});
      final raw = (parsed['candidates'] as List).cast<Map<String, dynamic>>();
      final suggestions = <Map<String, dynamic>>[];
      for (var i = 0; i < raw.length; i++) {
        final candidate = raw[i];
        suggestions.add({
          ...candidate,
          'fields': Map<String, dynamic>.from(candidate['fields'] as Map),
          'selected': candidate['select_default'] == true,
          'action_id': _newActionId(i),
          'done': false,
        });
      }
      final needsShopping = suggestions.any((c) => c['target'] == 'shopping');
      final lists = needsShopping
          ? await ref.read(shoppingApiProvider).getShoppingLists()
          : <Map<String, dynamic>>[];
      if (!mounted) return;
      setState(() {
        _candidates = suggestions;
        _classification = parsed['classification_source']?.toString();
        _lists = lists;
      });
    } catch (error) {
      if (mounted) setState(() => _error = '辨識失敗：請檢查連線或稍後再試（$error）');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _changeTarget(Map<String, dynamic> candidate, String target) {
    final original = _input.text.trim();
    setState(() {
      candidate['target'] = target;
      candidate['selected'] = false;
      candidate['fields'] = switch (target) {
        'note' => <String, dynamic>{'title': '', 'body': original},
        'task' => <String, dynamic>{'title': original},
        'shopping' => <String, dynamic>{'items': <Map<String, dynamic>>[{'name': original}]},
        _ => <String, dynamic>{'summary': original},
      };
    });
  }

  Future<void> _summarize(Map<String, dynamic> candidate) async {
    final fields = candidate['fields'] as Map<String, dynamic>;
    final url = fields['body']?.toString().trim() ?? '';
    if (!_isUrl(url) || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      // This explicit user click is the only operation that fetches the URL.
      final result = await ref.read(platformApiProvider).post(
          '/inbox/article-preview', {'url': url});
      final points = (result['key_points'] as List).map((v) => '- ' + v.toString()).join('\n');
      final pending = (result['uncertainties'] as List? ?? [])
          .map((v) => '- ' + v.toString()).join('\n');
      if (!mounted) return;
      setState(() {
        if ((fields['title'] ?? '').toString().trim().isEmpty) {
          fields['title'] = result['source_title']?.toString() ?? '';
        }
        fields['body'] = '原始網址：' + result['source_url'].toString() +
            '\n\n## 文章摘要\n' + points +
            (pending.isEmpty ? '' : '\n\n## 需要核對\n' + pending);
      });
    } catch (error) {
      if (mounted) setState(() => _error = '摘要無法取得，可只存網址（$error）');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _commit() async {
    if (_busy) return;
    final selected = _candidates.where((c) =>
        c['selected'] == true && c['done'] != true).toList();
    if (selected.isEmpty) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final payload = {
        'items': [
          for (final candidate in selected)
            {
              'action_id': candidate['action_id'],
              'target': candidate['target'],
              'fields': candidate['fields'],
            }
        ]
      };
      final result = await ref.read(platformApiProvider).post('/inbox/commit', payload);
      final receipts = (result['results'] as List).cast<Map<String, dynamic>>();
      if (!mounted) return;
      setState(() {
        _receipts = receipts;
        for (final receipt in receipts) {
          for (final candidate in _candidates) {
            if (candidate['action_id'] == receipt['action_id']) {
              // An UNKNOWN result must never be silently retried by the UI.
              candidate['done'] = true;
              candidate['selected'] = false;
            }
          }
        }
      });
    } catch (error) {
      if (mounted) setState(() => _error =
          '無法確認新增結果，請先檢查各功能中的資料，避免重複提交（$error）');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _field(Map<String, dynamic> fields, String key, String label,
      {int lines = 1}) {
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: TextFormField(
        key: ValueKey('capture-' + key),
        initialValue: fields[key]?.toString() ?? '',
        minLines: lines,
        maxLines: lines,
        decoration: InputDecoration(labelText: label, border: const OutlineInputBorder(),
            isDense: true),
        onChanged: (v) => fields[key] = v.isEmpty ? null : v,
      ),
    );
  }

  Widget _candidateCard(Map<String, dynamic> candidate, int index) {
    final fields = candidate['fields'] as Map<String, dynamic>;
    final target = candidate['target'].toString();
    final editable = candidate['done'] != true;
    return Card(
      key: ValueKey('capture-candidate-' + index.toString()),
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: CheckboxListTile(
              dense: true, contentPadding: EdgeInsets.zero,
              title: Text(switch (target) {
                'task' => '待辦', 'shopping' => '購物',
                'calendar' => '日曆', _ => '筆記',
              }),
              subtitle: Text(editable ? '確認後才會新增' : '已處理，避免重複送出'),
              value: candidate['selected'] == true && editable,
              onChanged: !editable ? null : (v) => setState(() => candidate['selected'] = v == true),
            )),
            DropdownButton<String>(
              value: target,
              onChanged: !editable ? null : (v) {
                if (v != null) _changeTarget(candidate, v);
              },
              items: const [
                DropdownMenuItem(value: 'task', child: Text('待辦')),
                DropdownMenuItem(value: 'shopping', child: Text('購物')),
                DropdownMenuItem(value: 'calendar', child: Text('日曆')),
                DropdownMenuItem(value: 'note', child: Text('筆記')),
              ],
            ),
          ]),
          if (target == 'note') ...[
            _field(fields, 'title', '筆記標題（可留白）'),
            _field(fields, 'body', '筆記內容', lines: 4),
            if (_isUrl(fields['body']?.toString() ?? '') &&
                ref.watch(effectiveFeaturesProvider).asData?.value?['life_inbox'] == true)
              TextButton.icon(
                onPressed: _busy || !editable ? null : () => _summarize(candidate),
                icon: const Icon(Icons.auto_awesome),
                label: const Text('擷取這個公開網址並製作摘要（可選）'),
              ),
          ] else if (target == 'task') ...[
            _field(fields, 'title', '待辦事項'),
            _field(fields, 'note', '備註（可選）'),
            _field(fields, 'due_at', '期限 ISO8601（不確定可留白）'),
          ] else if (target == 'calendar') ...[
            _field(fields, 'summary', '行程名稱'),
            _field(fields, 'start', '開始時間（ISO8601 含時區）'),
            _field(fields, 'end', '結束時間（ISO8601 含時區）'),
            _field(fields, 'start_date', '或全日開始日期 YYYY-MM-DD'),
            _field(fields, 'end_date', '或全日結束日期（exclusive）'),
          ] else ...[
            TextFormField(
              initialValue: (fields['items'] as List? ?? [])
                  .map((item) => (item as Map)['name'].toString()).join('、'),
              decoration: const InputDecoration(labelText: '品項（以頓號分隔）'),
              onChanged: (value) => fields['items'] = value.split(RegExp(r'[,，、]'))
                  .map((name) => name.trim())
                  .where((name) => name.isNotEmpty)
                  .map((name) => {'name': name}).toList(),
            ),
            if (_lists.isEmpty)
              const Padding(padding: EdgeInsets.only(top: 8),
                  child: Text('請先在購物功能建立清單，再返回選擇。'))
            else
              DropdownButtonFormField<String>(
                value: fields['shopping_list_id'] as String?,
                decoration: const InputDecoration(labelText: '存入哪一份購物清單？'),
                items: [
                  for (final list in _lists)
                    DropdownMenuItem(value: list['id'].toString(),
                        child: Text(list['name'].toString())),
                ],
                onChanged: (v) => setState(() {
                  fields['shopping_list_id'] = v;
                  candidate['selected'] = v != null;
                }),
              ),
          ],
          for (final warning in (candidate['ambiguities'] as List? ?? []))
            Padding(padding: const EdgeInsets.only(top: 4),
                child: Text(warning.toString(),
                    style: TextStyle(color: Theme.of(context).colorScheme.error))),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final selected = _candidates.where((c) =>
        c['selected'] == true && c['done'] != true).length;
    return Scaffold(
      appBar: AppBar(title: const Text('生活收件匣 · 快速新增')),
      body: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 860),
          child: ListView(padding: const EdgeInsets.all(16), children: [
            const Text('輸入一段文字或網址，Life 會提出建議；只有確認後才會寫入。'),
            const SizedBox(height: 12),
            TextField(
              key: const ValueKey('capture-input'),
              controller: _input, maxLines: 4, minLines: 2,
              maxLength: 1200,
              decoration: const InputDecoration(
                  border: OutlineInputBorder(), hintText: '例如：買牛奶、雞蛋；或貼上文章網址'),
            ),
            FilledButton.icon(
              onPressed: _busy ? null : _interpret,
              icon: const Icon(Icons.auto_awesome), label: const Text('智慧辨識'),
            ),
            if (_busy) const Padding(padding: EdgeInsets.all(14),
                child: LinearProgressIndicator()),
            if (_error != null)
              Padding(padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(_error!,
                    style: TextStyle(color: Theme.of(context).colorScheme.error))),
            if (_candidates.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text('辨識建議（來源：' + (_classification ?? '未知') + '）',
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              for (var i = 0; i < _candidates.length; i++)
                _candidateCard(_candidates[i], i),
              FilledButton.icon(
                onPressed: selected > 0 && !_busy ? _commit : null,
                icon: const Icon(Icons.check), label: Text('確認新增所選 ' + selected.toString() + ' 項'),
              ),
            ],
            if (_receipts.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text('新增結果', style: Theme.of(context).textTheme.titleMedium),
              for (final receipt in _receipts)
                ListTile(
                  leading: Icon(receipt['status'] == 'CREATED' ||
                          receipt['status'] == 'ALREADY_APPLIED'
                      ? Icons.check_circle_outline : Icons.warning_amber_outlined),
                  title: Text(receipt['target'].toString() + ' · ' + receipt['status'].toString()),
                  subtitle: receipt['status'] == 'UNKNOWN'
                      ? const Text('結果不明，先到原功能查核，不要直接重送')
                      : null,
                ),
            ],
          ]),
        ),
      ),
    );
  }
}
