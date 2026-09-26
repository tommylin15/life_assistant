import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.models import schemas
from app.models.habit import Habit, HabitCompletion


class HabitsContractTests(unittest.TestCase):
    def test_habit_schema_contract_exists(self):
        for name in ('HabitCreate', 'HabitUpdate', 'HabitOut', 'HabitCompletionOut'):
            self.assertTrue(hasattr(schemas, name), name)

    def test_habits_router_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec('app.api.habits'))


class HabitsSchemaBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        required = ('HabitCreate', 'HabitUpdate', 'HabitOut', 'HabitCompletionOut')
        if not all(hasattr(schemas, name) for name in required):
            raise unittest.SkipTest('Habit schemas not implemented yet')

    def test_create_requires_title_and_recurrence_rule_and_reminder_is_optional(self):
        body = schemas.HabitCreate(title='Walk', recurrence_rule='daily')
        self.assertEqual(body.reminder_time, None)
        with self.assertRaises(ValidationError):
            schemas.HabitCreate(recurrence_rule='daily')
        with self.assertRaises(ValidationError):
            schemas.HabitCreate(title='Walk')

    def test_update_rejects_empty_patch_and_null_required_fields(self):
        with self.assertRaises(ValidationError):
            schemas.HabitUpdate()
        with self.assertRaises(ValidationError):
            schemas.HabitUpdate(title=None)
        with self.assertRaises(ValidationError):
            schemas.HabitUpdate(recurrence_rule=None)
        self.assertIsNone(schemas.HabitUpdate(reminder_time=None).reminder_time)

    def test_habit_out_exposes_is_active(self):
        now = datetime.now(timezone.utc)
        out = schemas.HabitOut(
            id='h1',
            title='Walk',
            recurrence_rule='daily',
            reminder_time=None,
            is_active=True,
            created_at=now,
        )
        self.assertTrue(out.is_active)


class HabitsModelContractTests(unittest.TestCase):
    def test_habit_model_default_is_active_true(self):
        default = Habit.__table__.c.is_active.default
        self.assertIsNotNone(default)
        self.assertTrue(default.arg)


@unittest.skipUnless(importlib.util.find_spec('app.api.habits'), 'Habits router not implemented yet')
class HabitsRouterBehaviorTests(unittest.IsolatedAsyncioTestCase):

    async def test_list_filters_active_habits_only(self):
        from app.api.habits import list_habits
        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result

        await list_habits({'sub': 'u'}, db)
        statement = db.execute.await_args.args[0]
        self.assertIn('habits.is_active IS true', str(statement))

    async def test_missing_habit_complete_returns_404(self):
        from app.api.habits import complete_habit
        db = AsyncMock()
        db.get.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            await complete_habit('missing', {'sub': 'u'}, db)
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_complete_appends_distinct_rows_without_mutating_prior_completion(self):
        from app.api.habits import complete_habit
        habit = Habit(id='h1', title='Walk', recurrence_rule='daily')
        db = AsyncMock()
        db.add = MagicMock()
        db.get.return_value = habit
        completions = []

        def add(obj):
            if isinstance(obj, HabitCompletion):
                completions.append(obj)
        db.add.side_effect = add

        async def refresh(obj):
            if isinstance(obj, HabitCompletion) and obj.completed_at is None:
                obj.completed_at = datetime.now(timezone.utc)
        db.refresh.side_effect = refresh

        with patch('app.api.habits.start_execution', new=AsyncMock(return_value=object())), \
             patch('app.api.habits.finish_execution', new=AsyncMock()), \
             patch('app.api.habits.fail_execution', new=AsyncMock()):
            first = await complete_habit('h1', {'sub': 'u'}, db)
            first_id = first.id
            second = await complete_habit('h1', {'sub': 'u'}, db)

        self.assertEqual(len(completions), 2)
        self.assertNotEqual(first_id, second.id)
        self.assertEqual(completions[0].id, first_id)

    async def test_history_orders_completed_at_descending(self):
        from app.api.habits import list_habit_completions
        habit = Habit(id='h1', title='Walk', recurrence_rule='daily')
        db = AsyncMock()
        db.get.return_value = habit
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result

        await list_habit_completions('h1', {'sub': 'u'}, db)
        statement = db.execute.await_args.args[0]
        sql = str(statement)
        self.assertIn('ORDER BY habit_completions.completed_at DESC', sql)

    def test_router_exposes_no_delete_activate_or_deactivate_mutation(self):
        from app.api.habits import router
        paths_methods = {(route.path, tuple(sorted(route.methods or []))) for route in router.routes}
        for path, methods in paths_methods:
            self.assertNotIn('DELETE', methods)
            self.assertNotIn('/activate', path)
            self.assertNotIn('/deactivate', path)


class HabitsMainRegistrationTests(unittest.TestCase):
    def test_main_registers_habits_router(self):
        path = Path(__file__).parents[1] / 'app/main.py'
        source = path.read_text()
        self.assertIn('from app.api.habits import router as habits_router', source)
        self.assertIn('app.include_router(habits_router, prefix="/api/v1")', source)


class HabitsHttpContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_unauthenticated_habits_returns_401_with_request_id(self):
        if not importlib.util.find_spec('app.api.habits'):
            self.skipTest('Habits router not implemented yet')
        import httpx
        from fastapi import FastAPI, Request
        from app.api.habits import router

        app = FastAPI()
        @app.middleware('http')
        async def request_id_middleware(request: Request, call_next):
            response = await call_next(request)
            response.headers['X-Request-ID'] = 'task3-test'
            return response
        app.include_router(router, prefix='/api/v1')

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/api/v1/habits')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers.get('X-Request-ID'), 'task3-test')


class HabitsSourceContractTests(unittest.TestCase):
    def test_mutations_use_life_assistant_audit_actions(self):
        path = Path(__file__).parents[1] / 'app/api/habits.py'
        if not path.exists():
            self.skipTest('Habits router not implemented yet')
        source = path.read_text()
        for action in ('habit.create', 'habit.update', 'habit.complete'):
            self.assertIn(action, source)
        self.assertIn('provider="life_assistant"', source)


if __name__ == '__main__':
    unittest.main()
