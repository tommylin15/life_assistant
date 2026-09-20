import 'package:drift/native.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:life_assistant/app/app.dart';
import 'package:life_assistant/app/providers.dart';
import 'package:life_assistant/application/app_lock.dart';
import 'package:life_assistant/data/db/app_database.dart';

class _NoLock extends AppLockService {
  @override
  Future<bool> get hasPin async => false;
  @override
  Future<bool> authenticateBiometric() async => true;
}

void main() {
  testWidgets('shows local-first onboarding', (tester) async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    addTearDown(db.close);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          databaseProvider.overrideWithValue(db),
          appLockProvider.overrideWithValue(_NoLock()),
        ],
        child: const LifeAssistantApp(),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('你的資料留在本機'), findsOneWidget);
    expect(find.text('下一步'), findsOneWidget);
  });
}
