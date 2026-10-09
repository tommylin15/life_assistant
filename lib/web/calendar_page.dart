import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../app/design_system/app_components.dart';
import '../app/theme/app_tokens.dart';
import 'browser_navigation.dart';
import 'calendar_api.dart';

DateTime _dateOnly(DateTime date) => DateTime(date.year, date.month, date.day);
DateTime _monthOnly(DateTime date) => DateTime(date.year, date.month);
String _dayText(DateTime date) => DateFormat('yyyy/M/d').format(date);

class _CalendarEvent {
  _CalendarEvent(Map<String, dynamic> data)
      : id = (data['id'] as String?) ?? '',
        title = (data['summary'] as String?)?.trim().isNotEmpty == true
            ? data['summary'] as String
            : '未命名行程',
        description = (data['description'] as String?) ?? '',
        location = (data['location'] as String?) ?? '',
        start = _readDate(data['start']),
        end = _readDate(data['end']),
        allDay = (data['start'] as Map?)?['dateTime'] == null;

  final String id;
  final String title;
  final String description;
  final String location;
  final DateTime start;
  final DateTime end;
  final bool allDay;

  static DateTime _readDate(dynamic raw) {
    final field = raw is Map ? raw : const <String, dynamic>{};
    final timed = field['dateTime'] as String?;
    if (timed != null) {
      return DateTime.tryParse(timed)?.toLocal() ?? DateTime(1970);
    }
    // All-day end.date is exclusive; never shift a civil date across time zones.
    return DateTime.tryParse((field['date'] as String?) ?? '') ??
        DateTime(1970);
  }

  bool occursOn(DateTime day) {
    final startOfDay = _dateOnly(day);
    final nextDay = startOfDay.add(const Duration(days: 1));
    return start.isBefore(nextDay) && end.isAfter(startOfDay);
  }

  String period(BuildContext context) {
    if (allDay) {
      final lastDay = end.subtract(const Duration(days: 1));
      return start.year == lastDay.year &&
              start.month == lastDay.month &&
              start.day == lastDay.day
          ? _dayText(start) + ' · 全天'
          : _dayText(start) + ' — ' + _dayText(lastDay) + ' · 全天';
    }
    final first = _dayText(start) + ' ' +
        TimeOfDay.fromDateTime(start).format(context);
    final second = _dayText(end) + ' ' +
        TimeOfDay.fromDateTime(end).format(context);
    return first + ' — ' + second;
  }
}

class _CalendarWorkspace {
  _CalendarWorkspace(this.connected, this.events);

  final bool connected;
  final List<_CalendarEvent> events;
}

final _calendarWorkspace = FutureProvider.family<_CalendarWorkspace, DateTime>(
  (ref, month) async {
    final api = ref.read(calendarApiProvider);
    final state = await api.status();
    final services = (state['granted_services'] as List? ?? const []);
    final connected = state['connected'] == true &&
        services.contains('calendar');
    if (!connected) return _CalendarWorkspace(false, const []);
    final next = DateTime(month.year, month.month + 1);
    final data = await api.events(month, next);
    final events = data.map(_CalendarEvent.new).toList()
      ..sort((a, b) => a.start.compareTo(b.start));
    return _CalendarWorkspace(true, events);
  },
);

class CalendarPage extends ConsumerStatefulWidget {
  const CalendarPage({super.key});

  @override
  ConsumerState<CalendarPage> createState() => _CalendarPageState();
}

class _CalendarPageState extends ConsumerState<CalendarPage> {
  late DateTime _month = _monthOnly(DateTime.now());
  late DateTime _selectedDay = _dateOnly(DateTime.now());
  bool _showDay = false;
  bool _busy = false;

  void _reload() => ref.invalidate(_calendarWorkspace(_month));

  void _moveMonth(int change) {
    setState(() {
      _month = DateTime(_month.year, _month.month + change);
      _selectedDay = DateTime(_month.year, _month.month, 1);
      _showDay = false;
    });
  }

  Future<void> _chooseDay() async {
    final value = await showDatePicker(
      context: context,
      initialDate: _selectedDay,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (value == null || !mounted) return;
    setState(() {
      _selectedDay = _dateOnly(value);
      _month = _monthOnly(value);
      _showDay = true;
    });
  }

  void _notify(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _edit([_CalendarEvent? event]) async {
    if (_busy) return;
    final body = await showDialog<Map<String, dynamic>>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _CalendarEditor(
        event: event,
        selectedDay: _selectedDay,
      ),
    );
    if (body == null || !mounted) return;
    setState(() => _busy = true);
    try {
      final api = ref.read(calendarApiProvider);
      if (event == null) {
        await api.create(body);
      } else {
        await api.update(event.id, body);
      }
      _reload();
      if (mounted) _notify(event == null ? '行程已新增' : '行程已更新');
    } catch (error) {
      if (mounted) _notify('儲存行程失敗：$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _delete(_CalendarEvent event) async {
    if (_busy || event.id.isEmpty) return;
    final confirmed = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => AlertDialog(
        title: const Text('確認刪除行程'),
        content: Text('確定要從 Google Calendar 刪除「' + event.title +
            '」嗎？這個操作無法在生活助理中復原。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('確認刪除'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await ref.read(calendarApiProvider).deleteConfirmed(event.id);
      _reload();
      if (mounted) _notify('行程已刪除');
    } catch (error) {
      if (mounted) _notify('刪除行程失敗：$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = ref.watch(_calendarWorkspace(_month));
    final workspace = result.asData?.value;
    final wide = MediaQuery.sizeOf(context).width >= AppBreakpoints.pageActions;

    return Scaffold(
      appBar: AppBar(
        title: const Text('日曆'),
        actions: [
          IconButton(
            tooltip: '重新整理行程',
            onPressed: _busy ? null : _reload,
            icon: const Icon(Icons.refresh),
          ),
          if (wide && workspace?.connected == true)
            Padding(
              padding: const EdgeInsets.only(right: AppSpacing.lg),
              child: FilledButton.icon(
                onPressed: _busy ? null : () => _edit(),
                icon: const Icon(Icons.add),
                label: const Text('新增行程'),
              ),
            ),
        ],
      ),
      floatingActionButton: !wide && workspace?.connected == true
          ? FloatingActionButton(
              tooltip: '新增行程',
              onPressed: _busy ? null : () => _edit(),
              child: const Icon(Icons.add),
            )
          : null,
      body: result.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => AppStatePanel(
          title: '無法載入日曆',
          message: '$error',
          icon: const Icon(Icons.cloud_off_outlined),
          action: FilledButton.icon(
            onPressed: _reload,
            icon: const Icon(Icons.refresh),
            label: const Text('重試'),
          ),
        ),
        data: (value) => value.connected
            ? _content(value)
            : AppStatePanel(
                title: '尚未連結 Google Calendar',
                message: '授權日曆後即可查看及管理你的 Google 行程。',
                icon: const Icon(Icons.event_busy_outlined),
                action: FilledButton.icon(
                  onPressed: () => navigateBrowser(
                    ref.read(calendarApiProvider).authorizationUrl(),
                  ),
                  icon: const Icon(Icons.link),
                  label: const Text('連結 Google Calendar'),
                ),
              ),
      ),
    );
  }

  Widget _content(_CalendarWorkspace value) {
    final visibleEvents = _showDay
        ? value.events.where((e) => e.occursOn(_selectedDay)).toList()
        : value.events;
    return RefreshIndicator(
      onRefresh: () async {
        _reload();
        await ref.read(_calendarWorkspace(_month).future);
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          AppPageFrame(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('我的 Google 行程',
                    style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: AppSpacing.xs),
                const Text('依月份瀏覽行程；選擇日期可查看當天事件。'),
                const SizedBox(height: AppSpacing.lg),
                Wrap(
                  spacing: AppSpacing.sm,
                  runSpacing: AppSpacing.sm,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    IconButton(
                      tooltip: '上一個月',
                      onPressed: () => _moveMonth(-1),
                      icon: const Icon(Icons.chevron_left),
                    ),
                    Text(DateFormat('yyyy / MM').format(_month),
                        style: Theme.of(context).textTheme.titleLarge),
                    IconButton(
                      tooltip: '下一個月',
                      onPressed: () => _moveMonth(1),
                      icon: const Icon(Icons.chevron_right),
                    ),
                    OutlinedButton.icon(
                      onPressed: _chooseDay,
                      icon: const Icon(Icons.event_outlined),
                      label: Text('選擇日期 ' + _dayText(_selectedDay)),
                    ),
                    TextButton(
                      onPressed: () {
                        final today = DateTime.now();
                        setState(() {
                          _month = _monthOnly(today);
                          _selectedDay = _dateOnly(today);
                          _showDay = true;
                        });
                      },
                      child: const Text('今天'),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                Wrap(
                  spacing: AppSpacing.sm,
                  children: [
                    ChoiceChip(
                      label: const Text('整月'),
                      selected: !_showDay,
                      onSelected: (_) => setState(() => _showDay = false),
                    ),
                    ChoiceChip(
                      label: const Text('選定日期'),
                      selected: _showDay,
                      onSelected: (_) => setState(() => _showDay = true),
                    ),
                    Padding(
                      padding: const EdgeInsets.all(AppSpacing.sm),
                      child: Text('共 ' + visibleEvents.length.toString() + ' 筆'),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                if (visibleEvents.isEmpty)
                  AppStatePanel(
                    title: _showDay ? '這一天沒有行程' : '本月還沒有行程',
                    message: '可新增一筆行程，或切換日期查看其他事件。',
                    icon: const Icon(Icons.event_available_outlined),
                    action: FilledButton.icon(
                      onPressed: _busy ? null : () => _edit(),
                      icon: const Icon(Icons.add),
                      label: const Text('新增行程'),
                    ),
                  )
                else
                  for (final event in visibleEvents) ...[
                    AppSectionCard(
                      title: event.title,
                      subtitle: event.period(context),
                      action: Wrap(
                        spacing: 0,
                        children: [
                          IconButton(
                            key: ValueKey('calendar-edit-' + event.id),
                            tooltip: '編輯行程：' + event.title,
                            onPressed: _busy ? null : () => _edit(event),
                            icon: const Icon(Icons.edit_outlined),
                          ),
                          IconButton(
                            key: ValueKey('calendar-delete-' + event.id),
                            tooltip: '刪除行程：' + event.title,
                            onPressed: _busy ? null : () => _delete(event),
                            icon: const Icon(Icons.delete_outline),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (event.allDay)
                            const AppStatusChip(label: '全天', icon: Icons.wb_sunny_outlined),
                          if (event.location.isNotEmpty)
                            Text('地點：' + event.location),
                          if (event.description.isNotEmpty)
                            Text(event.description),
                        ],
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                  ],
                const SizedBox(height: 76),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CalendarEditor extends StatefulWidget {
  const _CalendarEditor({required this.event, required this.selectedDay});
  final _CalendarEvent? event;
  final DateTime selectedDay;

  @override
  State<_CalendarEditor> createState() => _CalendarEditorState();
}

class _CalendarEditorState extends State<_CalendarEditor> {
  final _key = GlobalKey<FormState>();
  late final TextEditingController _title;
  late final TextEditingController _description;
  late final TextEditingController _location;
  late DateTime _start;
  late DateTime _end;
  late bool _allDay;
  String? _validation;

  @override
  void initState() {
    super.initState();
    _title = TextEditingController(text: widget.event?.title ?? '');
    _description = TextEditingController(text: widget.event?.description ?? '');
    _location = TextEditingController(text: widget.event?.location ?? '');
    _start = widget.event?.start ??
        DateTime(widget.selectedDay.year, widget.selectedDay.month,
            widget.selectedDay.day, 9);
    _allDay = widget.event?.allDay ?? false;
    final existingEnd = widget.event?.end;
    // Google end.date excludes the last displayed day.
    _end = _allDay && existingEnd != null
        ? DateTime(existingEnd.year, existingEnd.month, existingEnd.day - 1)
        : existingEnd ?? _start.add(const Duration(hours: 1));
  }

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    _location.dispose();
    super.dispose();
  }

  Future<void> _pickDate(bool begin) async {
    final original = begin ? _start : _end;
    final picked = await showDatePicker(
      context: context,
      initialDate: original,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked == null || !mounted) return;
    setState(() {
      final updated = DateTime(picked.year, picked.month, picked.day,
          original.hour, original.minute);
      if (begin) {
        final duration = _end.difference(_start);
        _start = updated;
        _end = updated.add(duration);
      } else {
        _end = updated;
      }
    });
  }

  Future<void> _pickTime(bool begin) async {
    final original = begin ? _start : _end;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(original),
    );
    if (time == null || !mounted) return;
    setState(() {
      final updated = DateTime(original.year, original.month, original.day,
          time.hour, time.minute);
      if (begin) {
        final duration = _end.difference(_start);
        _start = updated;
        _end = updated.add(duration);
      } else {
        _end = updated;
      }
    });
  }

  void _save() {
    if (!_key.currentState!.validate()) return;
    if (_allDay) {
      final firstDay = _dateOnly(_start);
      final lastDay = _dateOnly(_end);
      if (lastDay.isBefore(firstDay)) {
        setState(() => _validation = '結束日期不可早於開始日期');
        return;
      }
      final exclusiveEnd = DateTime(lastDay.year, lastDay.month, lastDay.day + 1);
      Navigator.pop(context, <String, dynamic>{
        'summary': _title.text.trim(),
        'description': _description.text.trim(),
        'location': _location.text.trim(),
        'start_date': DateFormat('yyyy-MM-dd').format(firstDay),
        'end_date': DateFormat('yyyy-MM-dd').format(exclusiveEnd),
      });
      return;
    }
    if (!_end.isAfter(_start)) {
      setState(() => _validation = '結束時間必須晚於開始時間');
      return;
    }
    Navigator.pop(context, <String, dynamic>{
      'summary': _title.text.trim(),
      'description': _description.text.trim(),
      'location': _location.text.trim(),
      'start': _start.toUtc().toIso8601String(),
      'end': _end.toUtc().toIso8601String(),
    });
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: Text(widget.event == null ? '新增行程' : '編輯行程'),
        content: SizedBox(
          width: 460,
          child: SingleChildScrollView(
            child: Form(
              key: _key,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextFormField(
                    key: const ValueKey('calendar-title-field'),
                    controller: _title,
                    autofocus: true,
                    maxLength: 500,
                    decoration: const InputDecoration(labelText: '行程名稱'),
                    validator: (value) => (value ?? '').trim().isEmpty
                        ? '請輸入行程名稱'
                        : null,
                  ),
                  TextFormField(
                    controller: _location,
                    maxLength: 1000,
                    decoration: const InputDecoration(labelText: '地點（選填）'),
                  ),
                  TextFormField(
                    controller: _description,
                    maxLength: 5000,
                    minLines: 1,
                    maxLines: 3,
                    decoration: const InputDecoration(labelText: '備註（選填）'),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  SwitchListTile(
                    title: const Text('全天行程'),
                    subtitle: const Text('全天活動的結束日期包含所選當天'),
                    value: _allDay,
                    onChanged: (value) => setState(() {
                      _allDay = value;
                      _validation = null;
                    }),
                  ),
                  for (final begin in [true, false]) ...[
                    Text(_allDay
                        ? (begin ? '開始日期' : '結束日期（含當天）')
                        : (begin ? '開始時間' : '結束時間')),
                    Wrap(
                      spacing: AppSpacing.sm,
                      children: [
                        OutlinedButton(
                          onPressed: () => _pickDate(begin),
                          child: Text(_dayText(begin ? _start : _end)),
                        ),
                        if (!_allDay)
                          OutlinedButton(
                            onPressed: () => _pickTime(begin),
                            child: Text(TimeOfDay.fromDateTime(
                              begin ? _start : _end,
                            ).format(context)),
                          ),
                      ],
                    ),
                  ],
                  if (_validation != null)
                    Text(_validation!,
                        style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ],
              ),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: _save,
            child: const Text('儲存'),
          ),
        ],
      );
}
