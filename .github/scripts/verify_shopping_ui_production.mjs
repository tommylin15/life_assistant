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
    lists: [
      {
        id: 'list-1',
        name: '生活用品',
        project_id: null,
        created_at: '2026-10-07T00:00:00Z',
        items: [
          {
            id: 'item-1',
            list_id: 'list-1',
            name: '牛奶',
            category: '生鮮',
            is_done: false,
            sort_order: 0,
          },
        ],
      },
    ],
    creates: [],
    itemCreates: [],
    updates: [],
    nextList: 2,
    nextItem: 2,
  };
}

async function mockApi(page, state) {
  await page.route('**/auth/me', (route) =>
    json(route, 200, {
      email: 'shopping-ui@example.invalid',
      name: 'Shopping UI',
    }),
  );

  await page.route('**/api/v1/**', (route) => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === '/api/v1/shopping-lists' && method === 'GET') {
      return json(route, 200, state.lists);
    }

    if (path === '/api/v1/shopping-lists' && method === 'POST') {
      const body = bodyOf(request);
      state.creates.push(body);
      const list = {
        id: `list-browser-${state.nextList++}`,
        name: body.name,
        project_id: body.project_id ?? null,
        created_at: '2026-10-07T01:00:00Z',
        items: [],
      };
      state.lists.unshift(list);
      return json(route, 201, list);
    }

    let match = path.match(/^\/api\/v1\/shopping-lists\/([^/]+)\/items$/);
    if (match && method === 'POST') {
      const listId = decodeURIComponent(match[1]);
      const body = bodyOf(request);
      const item = {
        id: `item-browser-${state.nextItem++}`,
        list_id: listId,
        name: body.name,
        category: body.category ?? null,
        is_done: false,
        sort_order: 0,
      };
      state.itemCreates.push({ listId, body });
      state.lists.find((entry) => entry.id === listId).items.push(item);
      return json(route, 201, item);
    }

    match = path.match(/^\/api\/v1\/shopping-items\/([^/]+)$/);
    if (match && method === 'PATCH') {
      const itemId = decodeURIComponent(match[1]);
      const body = bodyOf(request);
      state.updates.push({ itemId, body });
      for (const list of state.lists) {
        const item = list.items.find((entry) => entry.id === itemId);
        if (item) {
          Object.assign(item, body);
          return json(route, 200, item);
        }
      }
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
const esc = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

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

async function replaceText(locator, value, label) {
  await locator.click();
  await locator.press('Control+A').catch(() => {});
  await locator.press('Backspace').catch(() => {});
  await locator.pressSequentially(value, { delay: 15 });
  await locator.press('Tab');
  await delay(150);
  const actual = await locator.inputValue().catch(() => null);
  assert.equal(actual, value, `${label} DOM value did not match typed text`);
}

async function waitObserved(predicate, label) {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    if (predicate()) return;
    await delay(100);
  }
  throw new Error(`not observed: ${label}`);
}

const pass = (name) => console.log(`shopping_ui_check=${name}:PASS`);

async function desktop(context) {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1280, height: 900 });
  const state = initialState();
  await mockApi(page, state);

  await page.goto(`${baseUrl}/more/shopping`, { waitUntil: 'domcontentloaded' });
  await semantics(page);

  await named(page, '購物清單');
  await named(page, '生活用品');
  await named(page, '完成 0 / 1');
  await named(page, '牛奶');
  await named(page, '分類：生鮮');
  pass('list_category_progress');

  await (await named(page, '新增清單')).click();
  await replaceText(await textbox(page, /^清單名稱$/), '旅行採買', 'create list');
  await (await named(page, '儲存')).click();

  await waitObserved(
    () => state.creates.some((body) => body.name === '旅行採買'),
    'shopping list create',
  );
  await named(page, '旅行採買');
  pass('create_list');

  await (await named(page, '新增品項：旅行採買')).click();
  await replaceText(await textbox(page, /^品項名稱$/), '充電線', 'item name');
  await replaceText(await textbox(page, /分類（選填）/), '3C', 'item category');
  await (await named(page, '儲存')).click();

  await waitObserved(
    () => state.itemCreates.some((entry) => entry.body.name === '充電線'),
    'shopping item create',
  );
  await named(page, '充電線');
  await named(page, '分類：3C');
  pass('create_item');

  const toggle = page.getByText('充電線').locator('..').getByRole('checkbox');
  const fallbackToggle = page.getByRole('checkbox').last();
  const checkbox = (await toggle.count()) > 0 ? toggle : fallbackToggle;
  await checkbox.check();

  await waitObserved(
    () => state.updates.some((entry) => entry.body.is_done === true),
    'shopping item toggle',
  );
  await named(page, '完成 1 / 1');
  pass('toggle_item');

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
  await (await named(page, '購物清單')).click();
  await named(page, '生活用品');
  await named(page, '新增清單');
  await named(page, '新增品項：生活用品');
  assert.deepEqual(overflow, []);
  pass('mobile_navigation_controls');

  await page.screenshot({
    path: '/tmp/shopping-ui-acceptance.png',
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
  console.log('shopping_ui_acceptance=PASS');
} catch (error) {
  console.error(error);
  try {
    const page = browser.contexts().flatMap((context) => context.pages()).at(-1);
    if (page) {
      await page.screenshot({
        path: '/tmp/shopping-ui-acceptance.png',
        fullPage: true,
      });
    }
  } catch (_) {}
  process.exitCode = 1;
} finally {
  await browser.close();
}
