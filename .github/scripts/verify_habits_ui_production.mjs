import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const baseUrl = process.env.BASE_URL;
if (!baseUrl) throw new Error('BASE_URL is required');

const json = (route, status, body) =>
  route.fulfill({
    status,
    contentType: 'application/json; charset=utf-8',
    body: JSON.stringify(body),
  });

const bodyOf = (request) =>
  request.postData() ? JSON.parse(request.postData()) : {};

function initialState() {
  return {
    habits: [
      {
        id: 'habit-morning',
        title: '晨間快走',
        recurrence_rule: 'FREQ=DAILY',
        reminder_time: '07:30',
        is_active: true,
        created_at: '2026-10-06T00:00:00Z',
      },
    ],
    completions: new Map([
      [
        'habit-morning',
        [
          {
            id: 'completion-existing',
            habit_id: 'habit-morning',
            completed_at: '2026-10-07T00:15:00Z',
          },
        ],
      ],
    ]),
    creates: [],
    updates: [],
    completes: [],
    nextHabit: 1,
    nextCompletion: 1,
  };
}

async function mockApi(page, state) {
  await page.route('**/auth/me', (route) =>
    json(route, 200, {
      email: 'habits-ui@example.invalid',
      name: 'Habits UI',
    }),
  );

  await page.route('**/api/v1/**', (route) => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === '/api/v1/habits' && method === 'GET') {
      return json(route, 200, state.habits);
    }

    if (path === '/api/v1/habits' && method === 'POST') {
      const body = bodyOf(request);
      state.creates.push(body);
      const habit = {
        id: `habit-browser-${state.nextHabit++}`,
        is_active: true,
        created_at: '2026-10-07T01:00:00Z',
        ...body,
      };
      state.habits.unshift(habit);
      state.completions.set(habit.id, []);
      return json(route, 201, habit);
    }

    let match = path.match(/^\/api\/v1\/habits\/([^/]+)\/completions$/);
    if (match && method === 'GET') {
      const id = decodeURIComponent(match[1]);
      return json(route, 200, state.completions.get(id) ?? []);
    }

    match = path.match(/^\/api\/v1\/habits\/([^/]+)\/complete$/);
    if (match && method === 'POST') {
      const id = decodeURIComponent(match[1]);
      const completion = {
        id: `completion-browser-${state.nextCompletion++}`,
        habit_id: id,
        completed_at: '2026-10-07T01:30:00Z',
      };
      state.completes.push(id);
      const history = state.completions.get(id) ?? [];
      history.unshift(completion);
      state.completions.set(id, history);
      return json(route, 201, completion);
    }

    match = path.match(/^\/api\/v1\/habits\/([^/]+)$/);
    if (match && method === 'PATCH') {
      const id = decodeURIComponent(match[1]);
      const body = bodyOf(request);
      state.updates.push({ id, body });
      const index = state.habits.findIndex((item) => item.id === id);
      state.habits[index] = { ...state.habits[index], ...body };
      return json(route, 200, state.habits[index]);
    }

    return json(route, 404, { detail: `unexpected ${method} ${path}` });
  });
}

async function semantics(page) {
  await page.waitForSelector('flutter-view', { timeout: 30000 });
  const placeholder = page.locator('flt-semantics-placeholder');
  if ((await placeholder.count()) > 0) {
    await placeholder.first().evaluate((element) => element.click());
  } else {
    const enable = page.getByLabel('Enable accessibility', { exact: true });
    if ((await enable.count()) > 0) {
      await enable.first().evaluate((element) => element.click());
    }
  }
  await page.waitForTimeout(300);
}

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const esc = (text) => text.replace(/[.*+?^\${}()|[\]\\]/g, '\\$&');

async function visible(locators, timeout = 12000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    for (const locator of locators) {
      const count = await locator.count();
      for (let index = 0; index < count; index += 1) {
        if (await locator.nth(index).isVisible().catch(() => false)) {
          return locator.nth(index);
        }
      }
    }
    await delay(120);
  }
  throw new Error('visible locator not found');
}

async function named(page, text, timeout = 12000) {
  const pattern = text instanceof RegExp ? text : new RegExp(`^${esc(text)}$`);
  return visible(
    [
      page.getByRole('button', { name: pattern }),
      page.getByLabel(pattern),
      page.getByText(pattern),
    ],
    timeout,
  );
}

async function textbox(page, label) {
  const pattern = label instanceof RegExp ? label : new RegExp(esc(label));
  return visible(
    [
      page.getByRole('textbox', { name: pattern }),
      page.getByLabel(pattern),
    ],
    6000,
  );
}

async function replaceText(locator, value) {
  await locator.click();
  await locator.press('Control+A');
  await locator.press('Backspace');
  await locator.pressSequentially(value, { delay: 12 });
  await locator.press('Tab');
}

async function waitObserved(predicate, label) {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    if (predicate()) return;
    await delay(100);
  }
  throw new Error(`not observed: ${label}`);
}

const pass = (name) => console.log(`habits_ui_check=${name}:PASS`);

async function desktop(context) {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1280, height: 900 });
  const state = initialState();
  await mockApi(page, state);

  await page.goto(`${baseUrl}/more/habits`, { waitUntil: 'domcontentloaded' });
  await semantics(page);

  await named(page, '習慣');
  await named(page, '晨間快走');
  await named(page, '每日');
  await named(page, '提醒 07:30');
  await named(page, '完成紀錄 1 筆');
  pass('list_history_summary');

  await (await named(page, '新增習慣')).click();
  await replaceText(await textbox(page, /^名稱$/), '瀏覽器習慣');
  await replaceText(await textbox(page, /提醒時間/), '21:30');
  await (await named(page, '儲存')).click();

  await waitObserved(
    () => state.creates.some((body) => body.title === '瀏覽器習慣'),
    'habit create',
  );
  assert.equal(state.creates.at(-1).recurrence_rule, 'FREQ=DAILY');
  assert.equal(state.creates.at(-1).reminder_time, '21:30');
  await named(page, '瀏覽器習慣');
  pass('create');

  await (await named(page, '編輯習慣：瀏覽器習慣')).click();
  await replaceText(await textbox(page, /^名稱$/), '瀏覽器習慣更新');
  await replaceText(await textbox(page, /提醒時間/), '22:00');
  await (await named(page, '儲存')).click();

  await waitObserved(
    () => state.updates.some((entry) => entry.body.title === '瀏覽器習慣更新'),
    'habit update',
  );
  await named(page, '瀏覽器習慣更新');
  await named(page, '提醒 22:00');
  pass('update');

  await (await named(page, '記錄完成：瀏覽器習慣更新')).click();
  await waitObserved(
    () => state.completes.includes('habit-browser-1'),
    'habit completion',
  );
  await named(page, /已記錄「瀏覽器習慣更新」完成/);
  await named(page, '完成紀錄 1 筆');
  pass('complete');

  const historyButtons = page.getByRole('button', { name: /^完成紀錄$/ });
  await visible([historyButtons]);
  await historyButtons.first().click();
  await named(page, '瀏覽器習慣更新 · 完成紀錄');
  await named(page, /2026\/10\/7/);
  pass('history_dialog');

  await page.close();
}

async function mobile(context) {
  const page = await context.newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  const state = initialState();
  const overflow = [];
  page.on('console', (message) => {
    if (/RenderFlex overflowed|overflowed by/i.test(message.text())) {
      overflow.push(message.text());
    }
  });
  await mockApi(page, state);

  await page.goto(`${baseUrl}/more`, { waitUntil: 'domcontentloaded' });
  await semantics(page);
  await (await named(page, '習慣')).click();
  await named(page, '晨間快走');
  await named(page, '記錄完成：晨間快走');
  await named(page, '新增習慣');
  assert.deepEqual(overflow, []);
  pass('mobile_navigation_controls');

  await page.screenshot({
    path: '/tmp/habits-ui-acceptance.png',
    fullPage: true,
  });
  await page.close();
}

const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({
    serviceWorkers: 'block',
    locale: 'zh-TW',
    timezoneId: 'Asia/Taipei',
  });
  await desktop(context);
  await mobile(context);
  await context.close();
  console.log('habits_ui_acceptance=PASS');
} catch (error) {
  console.error(error);
  try {
    const page = browser.contexts().flatMap((context) => context.pages()).at(-1);
    if (page) {
      await page.screenshot({
        path: '/tmp/habits-ui-acceptance.png',
        fullPage: true,
      });
    }
  } catch (_) {}
  process.exitCode = 1;
} finally {
  await browser.close();
}
