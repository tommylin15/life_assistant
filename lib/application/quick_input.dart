import '../domain/models.dart';

class ParsedTask {
  const ParsedTask({
    required this.title,
    this.dueAt,
    this.priority = ItemPriority.normal,
  });
  final String title;
  final DateTime? dueAt;
  final ItemPriority priority;
}

class QuickInputParser {
  const QuickInputParser();

  ParsedTask parse(String input, {DateTime? now}) {
    final base = now ?? DateTime.now();
    var title = input.trim();
    DateTime? due;
    if (title.contains('明天')) {
      final next = base.add(const Duration(days: 1));
      due = DateTime(next.year, next.month, next.day, 18);
      title = title.replaceAll('明天', '').trim();
    } else if (title.contains('今天') || title.contains('今晚')) {
      due = DateTime(
        base.year,
        base.month,
        base.day,
        title.contains('今晚') ? 20 : 18,
      );
      title = title.replaceAll(RegExp('今天|今晚'), '').trim();
    }
    final date = RegExp(r'(\d{1,2})[\/-](\d{1,2})(?:\s*前)?').firstMatch(title);
    if (date != null) {
      var year = base.year;
      var value = DateTime(
        year,
        int.parse(date.group(1)!),
        int.parse(date.group(2)!),
        18,
      );
      if (value.isBefore(DateTime(base.year, base.month, base.day)))
        value = DateTime(++year, value.month, value.day, 18);
      due = value;
      title = title.replaceFirst(date.group(0)!, '').trim();
    }
    final weekday = RegExp(r'(?:週|星期)([一二三四五六日天])').firstMatch(title);
    if (weekday != null) {
      const values = {
        '一': 1,
        '二': 2,
        '三': 3,
        '四': 4,
        '五': 5,
        '六': 6,
        '日': 7,
        '天': 7,
      };
      var add = values[weekday.group(1)]! - base.weekday;
      if (add <= 0) add += 7;
      final value = base.add(Duration(days: add));
      due = DateTime(value.year, value.month, value.day, 18);
      title = title.replaceFirst(weekday.group(0)!, '').trim();
    }
    final time = RegExp(r'(上午|下午|晚上)?\s*(\d{1,2})\s*[點时時]').firstMatch(title);
    if (time != null) {
      var hour = int.parse(time.group(2)!);
      if (time.group(1) != null && time.group(1) != '上午' && hour < 12)
        hour += 12;
      final date = due ?? base;
      due = DateTime(date.year, date.month, date.day, hour);
      title = title.replaceFirst(time.group(0)!, '').trim();
    }
    final high = title.contains('重要') || title.contains('緊急');
    title = title.replaceAll(RegExp('重要|緊急'), '').trim();
    return ParsedTask(
      title: title.isEmpty ? input.trim() : title,
      dueAt: due,
      priority: high ? ItemPriority.high : ItemPriority.normal,
    );
  }
}
