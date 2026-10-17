import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'platform_api.dart';
import 'inbox_article_errors.dart';
import 'shopping_api.dart';

/// Single, account-gated capture surface. Suggestions never persist until commit.
class LifeCapturePage extends ConsumerStatefulWidget {
  const LifeCapturePage({super.key, this.gmailRadarItemId});

  final String? gmailRadarItemId;

  @override
  ConsumerState<LifeCapturePage> createState() => _LifeCapturePageState();
}

class _LifeCapturePageState extends ConsumerState<LifeCapturePage> {
  @override
  void initState() {
    super.initState();
    if (widget.gmailRadarItemId != null) _loadGmailHandoff();
  }

  Future<void> _loadGmailHandoff() async {
    try {
      final data = await ref.read(platformApiProvider).get(
        '/integrations/google/gmail/radar/items/' +
            Uri.encodeComponent(widget.gmailRadarItemId!) + '/handoff');
      if (!mounted) return;
      setState(() {
        _input.text = data['text']?.toString() ?? '';
        _gmailActionId = data['action_id']?.toString();
      });
    } catch (_) {
      if (mounted) setState(() => _gmailTransferError =
          '無法取得這筆 Gmail 事項，或已成功存入其他功能；請返回 Gmail 雷達查看。');
    }
  }

  final _input = TextEditingController();
  bool _busy = false;
  String? _error;
  String? _classification;
  List<Map<String, dynamic>> _candidates = [];
  List<Map<String, dynamic>> _lists = [];
  List<Map<String, dynamic>> _receipts = [];
  String? _gmailActionId;
  Map<String, dynamic>? _linkedResult;
  String? _gmailTransferError;

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
        if (_gmailActionId != null && i > 0) break;
        final suggestion = <String, dynamic>{
          ...candidate,
          'date_hint': parsed['date_hint'],
          'fields': Map<String, dynamic>.from(candidate['fields'] as Map),
          'selected': candidate['select_default'] == true,
          'action_id': _gmailActionId ?? _newActionId(i),
          'done': false,
        };
        _applyDateHint(suggestion);
        suggestions.add(suggestion);
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
      _applyDateHint(candidate);
    });
  }

  // Store dates in the Life application's fixed Asia/Taipei timezone. The
  // browser's local timezone may differ; never use toLocal() for date evidence.
  String _ymd(DateTime day) => day.year.toString().padLeft(4, '0') + '-' +
      day.month.toString().padLeft(2, '0') + '-' +
      day.day.toString().padLeft(2, '0');

  String _tpeDateTime(DateTime day, TimeOfDay time) =>
      _ymd(day) + 'T' + time.hour.toString().padLeft(2, '0') + ':' +
      time.minute.toString().padLeft(2, '0') + ':00+08:00';

  DateTime? _parseDay(dynamic raw) {
    final value = raw?.toString();
    if (value == null || value.length < 10) return null;
    final day = DateTime.tryParse(value.substring(0, 10));
    if (day == null || _ymd(day) != value.substring(0, 10)) return null;
    return day;
  }

  DateTime? _tpeWallTime(dynamic raw) {
    final parsed = DateTime.tryParse(raw?.toString() ?? '');
    if (parsed == null) return null;
    final wall = parsed.toUtc().add(const Duration(hours: 8));
    return DateTime(wall.year, wall.month, wall.day, wall.hour, wall.minute);
  }

  DateTime? _dateFromHint(Map<String, dynamic> candidate) {
    final hint = candidate['date_hint'];
    if (hint is! Map) return null;
    final precision = hint['precision']?.toString();
    if (precision == 'day') return _parseDay(hint['date']);
    final y = hint['year'] as int? ?? DateTime.now().year;
    final m = hint['month'] as int?;
    final d = hint['day'] as int? ?? 1;
    if (m == null || m < 1 || m > 12) return null;
    final result = DateTime(y, m, d);
    // e.g. Feb 29 without year: let the user choose a valid year in picker.
    return result.month == m && result.day == d ? result : DateTime(y, m, 1);
  }

  String? _hintText(Map<String, dynamic> candidate) {
    final hint = candidate['date_hint'];
    if (hint is! Map) return null;
    final source = hint['raw']?.toString() ?? '';
    return switch (hint['precision']) {
      'day' => '已辨識日期：$source（可點日期修改）',
      'year_month' => '原文只有「$source」，缺少日期，請從萬年曆選一天',
      'month_day' => '原文只有「$source」，缺少年份，請在萬年曆確認年份',
      'ambiguous' => '原文有多個日期「$source」，請自行確認要使用的日期',
      'invalid' => '無效日期「$source」，請在萬年曆選擇正確日期',
      _ => null,
    };
  }

  void _applyDateHint(Map<String, dynamic> candidate) {
    final hint = candidate['date_hint'];
    if (hint is! Map || hint['precision'] != 'day') return;
    final day = _dateFromHint(candidate);
    if (day == null) return;
    final fields = candidate['fields'] as Map<String, dynamic>;
    if (candidate['target'] == 'task' && fields['due_at'] == null) {
      // A date-only deadline is displayed explicitly as end-of-day, not as
      // a source-provided time. No reminder is created.
      fields['due_at'] = _tpeDateTime(day, const TimeOfDay(hour: 23, minute: 59));
    } else if (candidate['target'] == 'calendar' &&
        fields['start'] == null && fields['end'] == null &&
        fields['start_date'] == null && fields['end_date'] == null) {
      fields['start_date'] = _ymd(day);
      fields['end_date'] = _ymd(day.add(const Duration(days: 1)));
      // AI may have warned about a missing end; a user can now view/edit
      // the proposed one-day all-day event before consenting to create it.
    }
  }

  Future<DateTime?> _pickDay(Map<String, dynamic> candidate, DateTime? existing) {
    final preferred = existing ?? _dateFromHint(candidate) ?? DateTime.now();
    return showDatePicker(
      context: context,
      initialDate: preferred,
      firstDate: DateTime(1900),
      lastDate: DateTime(2100),
      helpText: '選擇日期（可切換年份與月份）',
      cancelText: '取消',
      confirmText: '確認',
    );
  }

  Future<void> _chooseTaskDate(Map<String, dynamic> candidate, {bool timeOnly = false}) async {
    final fields = candidate['fields'] as Map<String, dynamic>;
    final previous = _tpeWallTime(fields['due_at']);
    final day = timeOnly ? previous :
        await _pickDay(candidate, previous);
    if (!mounted || day == null) return;
    var time = previous == null
        ? const TimeOfDay(hour: 23, minute: 59)
        : TimeOfDay(hour: previous.hour, minute: previous.minute);
    if (timeOnly) {
      final chosen = await showTimePicker(context: context,
          initialTime: time, helpText: '選擇待辦截止時間');
      if (!mounted || chosen == null) return;
      time = chosen;
    }
    setState(() {
      fields['due_at'] = _tpeDateTime(day, time);
      candidate['selected'] = true;
    });
  }

  Future<void> _chooseCalendarDate(
      Map<String, dynamic> candidate, {required bool end}) async {
    final fields = candidate['fields'] as Map<String, dynamic>;
    final start = _parseDay(fields['start_date']);
    final currentEnd = _parseDay(fields['end_date']);
    final inclusiveEnd = currentEnd?.subtract(const Duration(days: 1));
    final day = await _pickDay(candidate, end ? inclusiveEnd : start);
    if (!mounted || day == null) return;
    setState(() {
      if (end) {
        fields['end_date'] = _ymd(day.add(const Duration(days: 1)));
      } else {
        fields['start_date'] = _ymd(day);
        if (currentEnd == null || !currentEnd.isAfter(day)) {
          fields['end_date'] = _ymd(day.add(const Duration(days: 1)));
        }
      }
      candidate['selected'] = _parseDay(fields['start_date']) != null &&
          (_parseDay(fields['end_date'])?.isAfter(
              _parseDay(fields['start_date'])!) ?? false);
    });
  }

  Future<void> _chooseCalendarTime(
      Map<String, dynamic> candidate, {required bool end}) async {
    final fields = candidate['fields'] as Map<String, dynamic>;
    final key = end ? 'end' : 'start';
    final previous = _tpeWallTime(fields[key]);
    final date = await _pickDay(candidate, previous);
    if (!mounted || date == null) return;
    final chosen = await showTimePicker(
      context: context,
      helpText: end ? '選擇結束時間' : '選擇開始時間',
      initialTime: previous != null
          ? TimeOfDay(hour: previous.hour, minute: previous.minute)
          : TimeOfDay(hour: end ? 10 : 9, minute: 0),
    );
    if (!mounted || chosen == null) return;
    setState(() {
      fields[key] = _tpeDateTime(date, chosen);
      candidate['selected'] = _calendarTimedValid(fields);
    });
  }

  bool _calendarReady(Map<String, dynamic> candidate) {
    if (candidate['target'] != 'calendar') return true;
    final fields = candidate['fields'] as Map<String, dynamic>;
    final timed = fields['start'] != null || fields['end'] != null ||
        candidate['calendar_timed'] == true;
    if (timed) {
      return fields['start_date'] == null && fields['end_date'] == null &&
          _calendarTimedValid(fields);
    }
    final start = _parseDay(fields['start_date']);
    final end = _parseDay(fields['end_date']);
    return start != null && end != null && end.isAfter(start);
  }

  bool _dateWarningResolved(Map<String, dynamic> candidate, String warning) {
    final target = candidate['target'];
    if (target != 'calendar' && target != 'task') return false;
    final fields = candidate['fields'] as Map<String, dynamic>;
    final ready = target == 'calendar'
        ? _calendarReady(candidate) : fields['due_at'] != null;
    return ready &&
        (warning.contains('日期') || warning.contains('萬年曆') ||
         warning.contains('開始與結束時間') || warning.contains('缺少年份') ||
         warning.contains('補齊行程'));
  }

  bool _calendarTimedValid(Map<String, dynamic> fields) {
    final start = DateTime.tryParse(fields['start']?.toString() ?? '');
    final end = DateTime.tryParse(fields['end']?.toString() ?? '');
    return start != null && end != null && end.isAfter(start);
  }

  Widget _dateButton({
    required String keyValue, required String label,
    required String display, required VoidCallback? onPressed,
  }) {
    return Padding(
      padding: const EdgeInsets.only(top: 10),
      child: OutlinedButton.icon(
        key: ValueKey(keyValue),
        onPressed: onPressed,
        icon: const Icon(Icons.calendar_month),
        label: Align(alignment: Alignment.centerLeft,
          child: Text('$label：$display', textAlign: TextAlign.left)),
      ),
    );
  }

  Widget _calendarInputs(Map<String, dynamic> candidate, int index, bool editable) {
    final fields = candidate['fields'] as Map<String, dynamic>;
    final isTimed = candidate['calendar_timed'] == true ||
        (candidate['calendar_timed'] == null &&
            (fields['start'] != null || fields['end'] != null));
    final startDay = _parseDay(fields['start_date']);
    final endExclusive = _parseDay(fields['end_date']);
    final lastDay = endExclusive?.subtract(const Duration(days: 1));
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      SwitchListTile(
        key: ValueKey('capture-calendar-all-day-$index'),
        contentPadding: EdgeInsets.zero,
        title: const Text('全日行程'),
        subtitle: const Text('只有日期、不指定時間時使用；不用計算結束日'),
        value: !isTimed,
        onChanged: !editable || _busy ? null : (allDay) => setState(() {
          fields.remove('start');
          fields.remove('end');
          fields.remove('start_date');
          fields.remove('end_date');
          candidate['calendar_timed'] = !allDay;
          if (allDay) _applyDateHint(candidate);
          candidate['selected'] = false;
        }),
      ),
      if (!isTimed) ...[
        _dateButton(keyValue: 'capture-calendar-start-date-$index',
          label: '開始日期', display: startDay == null ? '點選萬年曆' : _ymd(startDay),
          onPressed: !editable || _busy ? null :
              () => _chooseCalendarDate(candidate, end: false)),
        _dateButton(keyValue: 'capture-calendar-end-date-$index',
          label: '結束日期（含當天）',
          display: lastDay == null ? '選填；預設當天' : _ymd(lastDay),
          onPressed: !editable || _busy ? null :
              () => _chooseCalendarDate(candidate, end: true)),
      ] else ...[
        _dateButton(keyValue: 'capture-calendar-start-time-$index',
          label: '開始日期與時間',
          display: fields['start']?.toString() ?? '點選萬年曆及時間',
          onPressed: !editable || _busy ? null :
              () => _chooseCalendarTime(candidate, end: false)),
        _dateButton(keyValue: 'capture-calendar-end-time-$index',
          label: '結束日期與時間',
          display: fields['end']?.toString() ?? '點選萬年曆及時間',
          onPressed: !editable || _busy ? null :
              () => _chooseCalendarTime(candidate, end: true)),
        if (fields['start'] != null && fields['end'] != null &&
            !_calendarTimedValid(fields))
          const Text('結束時間必須晚於開始時間',
              style: TextStyle(color: Colors.red)),
      ],
    ]);
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
      if (mounted) setState(() => _error = inboxArticleErrorMessage(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _commit() async {
    if (_busy) return;
    final selected = _candidates.where((c) =>
        c['selected'] == true && c['done'] != true && _calendarReady(c)).toList();
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
      if (_gmailActionId != null && widget.gmailRadarItemId != null &&
          receipts.any((receipt) =>
            receipt['action_id'] == _gmailActionId &&
            (receipt['status'] == 'CREATED' ||
             receipt['status'] == 'ALREADY_APPLIED'))) {
        try {
          final linked = await ref.read(platformApiProvider).post(
            '/integrations/google/gmail/radar/items/' +
              Uri.encodeComponent(widget.gmailRadarItemId!) + '/confirm-life-link',
            const {});
          if (mounted) setState(() => _linkedResult = linked);
        } catch (_) {
          if (mounted) setState(() => _gmailTransferError =
            '已儲存，但 Gmail 連結尚未確認。請不要再次建立項目，先回 Gmail 雷達重新查看。');
        }
      }
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
              value: candidate['selected'] == true && editable &&
                  _calendarReady(candidate),
              onChanged: !editable || !_calendarReady(candidate) ? null :
                  (v) => setState(() => candidate['selected'] = v == true),
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
                ref.watch(effectiveFeaturesProvider).asData?.value['life_inbox'] == true)
              TextButton.icon(
                onPressed: _busy || !editable ? null : () => _summarize(candidate),
                icon: const Icon(Icons.auto_awesome),
                label: const Text('擷取這個公開網址並製作摘要（可選）'),
              ),
          ] else if (target == 'task') ...[
            _field(fields, 'title', '待辦事項'),
            _field(fields, 'note', '備註（可選）'),
            _dateButton(
              keyValue: 'capture-task-due-$index',
              label: '截止日期',
              display: fields['due_at'] == null
                  ? '未設定（點選萬年曆）'
                  : (_tpeWallTime(fields['due_at']) == null
                      ? '請重新選擇'
                      : _ymd(_tpeWallTime(fields['due_at'])!) + ' ' +
                        _tpeWallTime(fields['due_at'])!.hour.toString().padLeft(2, '0') +
                        ':' + _tpeWallTime(fields['due_at'])!.minute.toString().padLeft(2, '0')),
              onPressed: !editable || _busy ? null : () => _chooseTaskDate(candidate)),
            if (fields['due_at'] != null) ...[
              const Text('未指定時間時，日期型待辦預設當天 23:59 截止（台灣時間）；不自動提醒。',
                  style: TextStyle(fontSize: 12)),
              TextButton.icon(
                key: ValueKey('capture-task-time-$index'),
                onPressed: !editable || _busy ? null :
                    () => _chooseTaskDate(candidate, timeOnly: true),
                icon: const Icon(Icons.schedule),
                label: const Text('調整截止時間'),
              ),
              TextButton(
                onPressed: !editable || _busy ? null : () => setState(() {
                  fields.remove('due_at');
                  candidate['selected'] = false;
                }),
                child: const Text('清除截止日期'),
              ),
            ],
          ] else if (target == 'calendar') ...[
            _field(fields, 'summary', '行程名稱'),
            _calendarInputs(candidate, index, editable),
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
                initialValue: fields['shopping_list_id'] as String?,
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
          if ((target == 'task' || target == 'calendar') &&
              _hintText(candidate) != null)
            Padding(
              padding: const EdgeInsets.only(top: 7),
              child: Text(_hintText(candidate)!,
                style: TextStyle(color: Theme.of(context).colorScheme.primary)),
            ),
          if (target == 'calendar' && !_calendarReady(candidate))
            const Padding(
              padding: EdgeInsets.only(top: 5),
              child: Text('請使用萬年曆補齊有效日期；有時間的行程需同時設定開始與結束。',
                  style: TextStyle(color: Colors.deepOrange)),
            ),
          for (final warning in (candidate['ambiguities'] as List? ?? []))
            if (!_dateWarningResolved(candidate, warning.toString()))
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
        c['selected'] == true && c['done'] != true && _calendarReady(c)).length;
    return Scaffold(
      appBar: AppBar(title: const Text('生活收件匣 · 快速新增')),
      body: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 860),
          child: ListView(padding: const EdgeInsets.all(16), children: [
            if (widget.gmailRadarItemId != null) ...[
              const Text('來自 Gmail 快掃：僅轉入這筆事項，不會自動建立資料。'),
              TextButton(onPressed: () => context.go('/more/gmail-radar'),
                child: const Text('返回 Gmail 雷達')),
              if (_gmailTransferError != null) Text(_gmailTransferError!),
              if (_linkedResult != null) ...[
                const Text('已完成：成功存入指定功能'),
                TextButton.icon(
                  onPressed: () => context.go(
                    _linkedResult!['target_route']?.toString() ?? '/today'),
                  icon: const Icon(Icons.open_in_new),
                  label: const Text('開啟已儲存的功能'),
                ),
              ],
            ],
            const Text('輸入一段文字或網址，Life 會提出建議；只有確認後才會寫入。'),
            const Text('待辦／行程日期可用萬年曆快速選擇；只有年月或月日會提示補選，無需輸入 ISO8601。',
                style: TextStyle(fontSize: 12)),
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
