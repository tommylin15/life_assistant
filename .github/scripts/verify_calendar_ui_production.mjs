import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const baseUrl = process.env.BASE_URL;
if (!baseUrl) throw new Error('BASE_URL is required');
const fixtureStart = '2026-10-10T01:00:00Z';
const fixtureEnd = '2026-10-10T02:00:00Z';

function initialState() {
  return {
    events: [
      {
        id: 'calendar-1',
        summary: '驗收會議',
        location: '會議室',
        start: { dateTime: fixtureStart },
        end: { dateTime: fixtureEnd },
      },
      {
        id: 'calendar-allday',
        summary: '全天假期',
        start: { date: '2026-10-09' },
        end: { date: '2026-10-10' },
      },
    ],
    creates: [], updates: [], deletes: [],
  };
}

function json(route, status, body) {
  return route.fulfill({
    status,
    contentType: 'application/json; charset=utf-8',
    body: JSON.stringify(body),
  });
}

async function mockApi(page, state) {
  await page.route('**/auth/me', route =>
    json(route, 200, { email: 'calendar-ui@example.invalid', name: 'Calendar UI' }));

  await page.route('**/api/v1/**', route => {
    const request = route.request();
    const method = request.method();
    const path = new URL(request.url()).pathname;
    const body = request.postData() ? JSON.parse(request.postData()) : {};

    if (path === '/api/v1/integrations/google/status' && method === 'GET') {
      return json(route, 200, { connected: true, granted_services: ['calendar'] });
    }
    if (path === '/api/v1/integrations/google/calendar/events') {
      if (method === 'GET') return json(route, 200, { events: state.events, returned: state.events.length });
      if (method === 'POST') {
        state.creates.push(body);
        const event = {
          id: 'calendar-new',
          summary: body.summary,
          description: body.description,
          location: body.location,
          start: { dateTime: body.start },
          end: { dateTime: body.end },
        };
        state.events.push(event);
        return json(route, 201, event);
      }
    }
    const match = path.match(/^\/api\/v1\/integrations\/google\/calendar\/events\/([^/]+)$/);
    if (match) {
      const id = decodeURIComponent(match[1]);
      if (method === 'PATCH') {
        state.updates.push({ id, body });
        const item = state.events.find(event => event.id === id);
        Object.assign(item, { summary: body.summary, start: { dateTime: body.start }, end: { dateTime: body.end } });
        return json(route, 200, item);
      }
      if (method === 'DELETE') {
        state.deletes.push({
          id, confirmation: request.headers()['x-life-assistant-confirmation'],
        });
        state.events = state.events.filter(event => event.id !== id);
        return route.fulfill({ status: 204, body: '' });
      }
    }
    return json(route, 404, { detail: 'unexpected ' + method + ' ' + path });
  });
}

async function semantics(page) {
  await page.waitForSelector('flutter-view', { timeout: 30000 });
  const placeholder = page.locator('flt-semantics-placeholder');
  if (await placeholder.count()) {
    await placeholder.first().evaluate(el => el.click());
  }
  await page.waitForTimeout(350);
}

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function named(page, name, timeout = 12000) {
  // Flutter Web merges event-card titles with neighboring semantic text.
  // Keep exact button targeting, but allow substring checks for read-only text.
  const pattern = name instanceof RegExp ? name : new RegExp(name);
  const exact = name instanceof RegExp ? name : new RegExp('^' + name + '$');
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    for (const locator of [
      page.getByRole('button', { name: exact }),
      page.getByLabel(pattern),
      page.getByText(pattern),
    ]) {
      const count = await locator.count();
      for (let i = 0; i < count; i++) {
        if (await locator.nth(i).isVisible().catch(() => false)) return locator.nth(i);
      }
    }
    await delay(150);
  }
  throw new Error('Calendar locator missing: ' + pattern);
}

// Flutter exposes event-card action semantics only within the scroll viewport.
async function eventAction(page, verb, title) {
  const expected = verb + '行程：' + title;
  await page.mouse.move(950, 650);
  await page.mouse.wheel(0, -3500);
  await delay(260);
  for (let scroll = 0; scroll < 12; scroll += 1) {
    const locators = [
      page.getByRole('button', { name: expected, exact: true }),
      page.getByLabel(expected, { exact: true }),
    ];
    for (const locator of locators) {
      for (let i = 0; i < await locator.count(); i += 1) {
        const item = locator.nth(i);
        if (await item.isVisible().catch(() => false)) {
          await item.click();
          return;
        }
      }
    }
    await page.mouse.wheel(0, 260);
    await delay(260);
  }
  const labels = await page.locator('[aria-label]').evaluateAll(elements =>
    elements.map(el => el.getAttribute('aria-label'))
      .filter(s => s && /行程：/.test(s)).slice(0, 20),
  );
  throw new Error('Missing Calendar action ' + expected +
    ' after scrolling; visibleLabels=' + JSON.stringify(labels));
}

async function observed(predicate, label) {
  for (let i = 0; i < 90; i++) {
    if (predicate()) return;
    await delay(100);
  }
  throw new Error('Calendar request missing: ' + label);
}

async function setTitle(page, value) {
  const input = page.getByRole('textbox', { name: /行程名稱/ });
  const el = await (async () => {
    if (await input.count()) return input.first();
    return page.getByLabel(/行程名稱/).first();
  })();
  await el.click();
  await el.press('Control+A');
  await el.pressSequentially(value, { delay: 15 });
  await el.press('Tab');
}

async function desktop(context) {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.clock.setFixedTime(new Date('2026-10-08T00:00:00Z'));
  const state = initialState();
  await mockApi(page, state);
  await page.goto(baseUrl + '/calendar', { waitUntil: 'domcontentloaded' });
  await semantics(page);

  await named(page, '我的 Google 行程');
  await named(page, '驗收會議');
  await named(page, '全天假期');
  console.log('calendar_ui_check=month_list_allday:PASS');

  await (await named(page, '新增行程')).click();
  await setTitle(page, '新建行程');
  await (await named(page, '儲存')).click();
  await observed(() => state.creates.some(item => item.summary === '新建行程'), 'create');
  assert.match(state.creates[0].start, /Z$/);
  await named(page, '新建行程');
  console.log('calendar_ui_check=create_tz:PASS');

  await (await named(page, '編輯行程：驗收會議')).click();
  await setTitle(page, '更新後的會議');
  await (await named(page, '儲存')).click();
  await observed(() => state.updates.some(item => item.id === 'calendar-1' && item.body.summary === '更新後的會議'), 'update');
  await named(page, '更新後的會議');
  console.log('calendar_ui_check=update:PASS');

  await eventAction(page, '刪除', '更新後的會議');
  await named(page, '確認刪除行程');
  assert.equal(state.deletes.length, 0, 'delete happened without confirmation');
  await (await named(page, '取消')).click();

  await eventAction(page, '刪除', '更新後的會議');
  await (await named(page, '確認刪除')).click();
  await observed(() => state.deletes.length === 1, 'delete');
  assert.equal(state.deletes[0].confirmation, 'explicit_user:calendar.delete:calendar-1');
  console.log('calendar_ui_check=confirmed_delete:PASS');

  await page.close();
}

async function mobile(context) {
  const page = await context.newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.clock.setFixedTime(new Date('2026-10-08T00:00:00Z'));
  const overflow = [];
  page.on('console', message => {
    if (/RenderFlex overflowed|overflowed by/i.test(message.text())) {
      overflow.push(message.text());
    }
  });
  await mockApi(page, initialState());
  await page.goto(baseUrl + '/calendar', { waitUntil: 'domcontentloaded' });
  await semantics(page);
  await named(page, '我的 Google 行程');
  await named(page, '驗收會議');
  await named(page, '新增行程');
  assert.deepEqual(overflow, []);
  console.log('calendar_ui_check=mobile_navigation_controls:PASS');
  await page.screenshot({ path: '/tmp/calendar-ui-acceptance.png', fullPage: true });
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
  console.log('calendar_ui_acceptance=PASS');
} catch (error) {
  console.error(error);
  for (const context of browser.contexts()) {
    for (const page of context.pages()) {
      await page.screenshot({ path: '/tmp/calendar-ui-acceptance.png', fullPage: true }).catch(() => {});
    }
  }
  process.exitCode = 1;
} finally {
  await browser.close();
}
