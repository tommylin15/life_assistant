import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:timezone/data/latest.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

class NotificationAdapter {
  NotificationAdapter({FlutterLocalNotificationsPlugin? plugin})
    : _plugin = plugin ?? FlutterLocalNotificationsPlugin();
  final FlutterLocalNotificationsPlugin _plugin;

  Future<void> initialize() async {
    tz.initializeTimeZones();
    final local = await FlutterTimezone.getLocalTimezone();
    tz.setLocalLocation(tz.getLocation(local.identifier));
    await _plugin.initialize(
      const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        iOS: DarwinInitializationSettings(),
      ),
    );
  }

  Future<bool> requestPermission() async {
    final implementation = _plugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >();
    final android = await implementation?.requestNotificationsPermission();
    await implementation?.requestExactAlarmsPermission();
    final ios = await _plugin
        .resolvePlatformSpecificImplementation<
          IOSFlutterLocalNotificationsPlugin
        >()
        ?.requestPermissions(alert: true, badge: true, sound: true);
    return android ?? ios ?? true;
  }

  Future<void> schedule({
    required int id,
    required String title,
    required String body,
    required DateTime at,
  }) => _plugin.zonedSchedule(
    id,
    title,
    body,
    tz.TZDateTime.from(at, tz.local),
    const NotificationDetails(
      android: AndroidNotificationDetails(
        'reminders',
        '提醒',
        channelDescription: '待辦、習慣與每日摘要提醒',
        importance: Importance.high,
        priority: Priority.high,
      ),
      iOS: DarwinNotificationDetails(),
    ),
    androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
    uiLocalNotificationDateInterpretation:
        UILocalNotificationDateInterpretation.absoluteTime,
  );

  Future<void> scheduleDaily({
    required int id,
    required String title,
    required String body,
    required int hour,
    required int minute,
  }) {
    final now = tz.TZDateTime.now(tz.local);
    var next = tz.TZDateTime(
      tz.local,
      now.year,
      now.month,
      now.day,
      hour,
      minute,
    );
    if (!next.isAfter(now)) next = next.add(const Duration(days: 1));
    return _plugin.zonedSchedule(
      id,
      title,
      body,
      next,
      const NotificationDetails(
        android: AndroidNotificationDetails('daily', '每日摘要'),
        iOS: DarwinNotificationDetails(),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
      matchDateTimeComponents: DateTimeComponents.time,
    );
  }

  Future<void> cancel(int id) => _plugin.cancel(id);
}
