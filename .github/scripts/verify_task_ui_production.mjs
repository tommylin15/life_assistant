import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const baseUrl = process.env.BASE_URL;
if (!baseUrl) {
  throw new Error('BASE_URL is required');
}

const projects = [{ id: 'p-work', name: '工作' }];
let nextTask = 1;
let nextChecklist = 1;
let tasks = [
  {
    id: 'task-open',
    title: '驗收初始待辦',
    note: '瀏覽器驗收資料',
    status: 'pending',
    priority: 'high',
    due_at: null,
    reminder_at: null,
    project_id: 'p-work',
  },
  {
    id: 'task-completed',
    title: '驗收已完成',
    note: null,
    status: 'completed',
    priority: 'normal',
    due_at: null,
    reminder_at: null,
    project_id: null,
  },
];
const checklists = new Map([
  [
    'task-open',
    [
      {
        id: 'check-initial',
        task_id: 'task-open',
        title: '初始檢查項目',
        is_done: false,
        sort_order: 0,
      },
    ],
  ],
]);

const observed = {
  taskCreate: null,
  taskUpdate: [],
  taskComplete: [],
  taskDelete: [],
  checklistCreate: [],
  checklistUpdate: [],
  checklistDelete: [],
};

function bodyOf(request) {
  const raw = request.postData();
  return raw ? JSON.parse(raw) : {};
}

function fulfillJson(route, status, payload) {
  return route.fulfill({
    status,
    contentType: 'application/json; charset=utf-8',
    body: JSON.stringify(payload),
  });
}

async function installApiMocks(page) {
  await page.route('**/auth/me', (route) =>
    fulfillJson(route, 200, {
      email: 'task-ui-acceptance@example.invalid',
      name: 'Task UI Acceptance',
    }),
  );

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const method = request.method();
    const { pathname } = new URL(request.url());

    if (pathname === '/api/v1/projects' && method === 'GET') {
      return fulfillJson(route, 200, projects);
    }

    if (pathname === '/api/v1/tasks' && method === 'GET') {
      return fulfillJson(route, 200, tasks);
    }

    if (pathname === '/api/v1/tasks' && method === 'POST') {
      const body = bodyOf(request);
      observed.taskCreate = body;
      const task = {
        id: `task-browser-${nextTask++}`,
        title: body.title,
        note: body.note ?? null,
        status: body.status ?? 'pending',
        priority: body.priority ?? 'normal',
        due_at: body.due_at ?? null,
        reminder_at: body.reminder_at ?? null,
        project_id: body.project_id ?? null,
      };
      tasks.push(task);
      checklists.set(task.id, []);
      return fulfillJson(route, 201, task);
    }

    const checklistCollection = pathname.match(
      /^\/api\/v1\/tasks\/([^/]+)\/checklist$/,
    );
    if (checklistCollection) {
      const taskId = decodeURIComponent(checklistCollection[1]);
      const items = checklists.get(taskId) ?? [];
      if (method === 'GET') {
        return fulfillJson(route, 200, items);
      }
      if (method === 'POST') {
        const body = bodyOf(request);
        const item = {
          id: `check-browser-${nextChecklist++}`,
          task_id: taskId,
          title: body.title,
          is_done: body.is_done ?? false,
          sort_order: body.sort_order ?? items.length,
        };
        items.push(item);
        checklists.set(taskId, items);
        observed.checklistCreate.push({ taskId, body });
        return fulfillJson(route, 201, item);
      }
    }

    const checklistItem = pathname.match(
      /^\/api\/v1\/tasks\/([^/]+)\/checklist\/([^/]+)$/,
    );
    if (checklistItem) {
      const taskId = decodeURIComponent(checklistItem[1]);
      const itemId = decodeURIComponent(checklistItem[2]);
      const items = checklists.get(taskId) ?? [];
      const index = items.findIndex((item) => item.id === itemId);
      if (index < 0) {
        return fulfillJson(route, 404, { detail: 'not found' });
      }
      if (method === 'PATCH') {
        const body = bodyOf(request);
        items[index] = { ...items[index], ...body };
        observed.checklistUpdate.push({ taskId, itemId, body });
        return fulfillJson(route, 200, items[index]);
      }
      if (method === 'DELETE') {
        items.splice(index, 1);
        observed.checklistDelete.push({ taskId, itemId });
        return route.fulfill({ status: 204, body: '' });
      }
    }

    const completeTask = pathname.match(/^\/api\/v1\/tasks\/([^/]+)\/complete$/);
    if (completeTask && method === 'POST') {
      const taskId = decodeURIComponent(completeTask[1]);
      const task = tasks.find((item) => item.id === taskId);
      if (!task) {
        return fulfillJson(route, 404, { detail: 'not found' });
      }
      task.status = 'completed';
      observed.taskComplete.push(taskId);
      return fulfillJson(route, 200, task);
    }

    const taskItem = pathname.match(/^\/api\/v1\/tasks\/([^/]+)$/);
    if (taskItem) {
      const taskId = decodeURIComponent(taskItem[1]);
      const index = tasks.findIndex((item) => item.id === taskId);
      if (index < 0) {
        return fulfillJson(route, 404, { detail: 'not found' });
      }
      if (method === 'PATCH') {
        const body = bodyOf(request);
        tasks[index] = { ...tasks[index], ...body };
        observed.taskUpdate.push({ taskId, body });
        return fulfillJson(route, 200, tasks[index]);
      }
      if (method === 'DELETE') {
        tasks.splice(index, 1);
        checklists.delete(taskId);
        observed.taskDelete.push(taskId);
        return route.fulfill({ status: 204, body: '' });
      }
    }

    console.error(`unexpected_api_request=${method} ${pathname}`);
    return fulfillJson(route, 404, { detail: 'unexpected acceptance request' });
  });
}

async function enableFlutterSemantics(page) {
  await page.waitForSelector('flutter-view', { timeout: 30000 });
  const placeholder = page.locator('flt-semantics-placeholder');
  if ((await placeholder.count()) > 0) {
    await placeholder.first().click({ force: true });
  } else {
    const enable = page.getByLabel('Enable accessibility', { exact: true });
    if ((await enable.count()) > 0) {
      await enable.first().click({ force: true });
    }
  }
  await page.waitForTimeout(300);
}

function exactPattern(text) {
  return new RegExp(`^${text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`);
}

async function visibleCandidate(locators, { last = false, timeout = 15000 } = {}) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    for (const locator of locators) {
      const count = await locator.count();
      const indexes = last
        ? Array.from({ length: count }, (_, i) => count - 1 - i)
        : Array.from({ length: count }, (_, i) => i);
      for (const index of indexes) {
        const candidate = locator.nth(index);
        if (await candidate.isVisible().catch(() => false)) {
          return candidate;
        }
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error('No visible matching semantics node found');
}

async function named(page, text, options = {}) {
  const pattern = options.exact === false ? new RegExp(text) : exactPattern(text);
  return visibleCandidate(
    [
      page.getByRole('button', { name: pattern }),
      page.getByRole('menuitem', { name: pattern }),
      page.getByRole('checkbox', { name: pattern }),
      page.getByLabel(pattern),
      page.getByText(pattern),
    ],
    options,
  );
}

async function textbox(page, name, fallbackIndex = 0) {
  const pattern = name instanceof RegExp ? name : new RegExp(name);
  try {
    return await visibleCandidate(
      [page.getByRole('textbox', { name: pattern }), page.getByLabel(pattern)],
      { timeout: 3000 },
    );
  } catch (_) {
    const visible = page.getByRole('textbox');
    const count = await visible.count();
    let seen = 0;
    for (let i = 0; i < count; i += 1) {
      const candidate = visible.nth(i);
      if (await candidate.isVisible().catch(() => false)) {
        if (seen === fallbackIndex) return candidate;
        seen += 1;
      }
    }
    throw new Error(`Textbox not found: ${name}`);
  }
}

async function isNamedVisible(page, text) {
  const pattern = new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const candidates = [page.getByLabel(pattern), page.getByText(pattern)];
  for (const locator of candidates) {
    const count = await locator.count();
    for (let i = 0; i < count; i += 1) {
      if (await locator.nth(i).isVisible().catch(() => false)) return true;
    }
  }
  return false;
}

async function waitNamed(page, text, expected = true, timeout = 10000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if ((await isNamedVisible(page, text)) === expected) return;
    await page.waitForTimeout(150);
  }
  throw new Error(`Expected ${JSON.stringify(text)} visible=${expected}`);
}

function taskByTitle(title) {
  return tasks.find((task) => task.title === title);
}

function record(check) {
  console.log(`task_ui_check=${check}:PASS`);
}

async function runDesktopAcceptance(context) {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1280, height: 900 });
  await installApiMocks(page);
  await page.goto(`${baseUrl}/tasks`, { waitUntil: 'domcontentloaded' });
  await enableFlutterSemantics(page);

  await waitNamed(page, '驗收初始待辦');
  await waitNamed(page, '工作');
  record('production_artifact_task_list');

  const search = await textbox(page, /搜尋待辦或備註/);
  await search.fill('不存在的驗收字串');
  await waitNamed(page, '驗收初始待辦', false);
  await search.fill('');
  await waitNamed(page, '驗收初始待辦');
  record('search');

  await (await named(page, '已完成')).click();
  await waitNamed(page, '驗收已完成');
  await (await named(page, '進行中')).click();
  await waitNamed(page, '驗收初始待辦');
  record('filters');

  await (await named(page, '新增待辦')).click();
  const title = await textbox(page, /標題/, 0);
  const note = await textbox(page, /備註/, 1);
  await title.fill('瀏覽器新增待辦');
  await note.fill('正式 Firebase artifact 驗收');
  await waitNamed(page, '優先度');
  await waitNamed(page, '專案');
  await waitNamed(page, '到期時間');
  await waitNamed(page, '提醒時間');
  await (await named(page, '儲存')).click();
  await waitNamed(page, '待辦已新增');
  await waitNamed(page, '瀏覽器新增待辦');
  assert.equal(observed.taskCreate?.title, '瀏覽器新增待辦');
  assert.equal(observed.taskCreate?.priority, 'normal');
  record('create_full_editor');

  await (await named(page, '待辦選項', { last: true })).click();
  await (await named(page, '編輯')).click();
  const editTitle = await textbox(page, /標題/, 0);
  await editTitle.fill('瀏覽器更新待辦');
  await (await named(page, '儲存')).click();
  await waitNamed(page, '待辦已更新');
  await waitNamed(page, '瀏覽器更新待辦');
  assert.ok(observed.taskUpdate.some(({ body }) => body.title === '瀏覽器更新待辦'));
  record('edit');

  await (await named(page, '待辦選項', { last: true })).click();
  await (await named(page, 'Checklist')).click();
  const checklistInput = await textbox(page, /新增 Checklist 項目/, 0);
  await checklistInput.fill('瀏覽器檢查項目');
  await checklistInput.press('Enter');
  await waitNamed(page, '瀏覽器檢查項目');
  assert.equal(observed.checklistCreate.length, 1);

  const visibleCheckboxes = page.getByRole('checkbox');
  let toggled = false;
  for (let i = (await visibleCheckboxes.count()) - 1; i >= 0; i -= 1) {
    const checkbox = visibleCheckboxes.nth(i);
    if (await checkbox.isVisible().catch(() => false)) {
      await checkbox.click();
      toggled = true;
      break;
    }
  }
  assert.equal(toggled, true, 'Checklist checkbox was not interactable');
  const checklistTask = taskByTitle('瀏覽器更新待辦');
  assert.ok(checklistTask, 'Updated task not found in acceptance state');
  const createdItems = checklists.get(checklistTask.id) ?? [];
  assert.equal(createdItems.at(-1)?.is_done, true);

  await (await named(page, '刪除項目', { last: true })).click();
  await waitNamed(page, '瀏覽器檢查項目', false);
  assert.equal(observed.checklistDelete.length, 1);
  record('checklist_crud');

  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  const completeControls = page.getByLabel('完成待辦', { exact: true });
  const complete = await visibleCandidate([completeControls], { last: true });
  await complete.click();
  assert.equal(taskByTitle('瀏覽器更新待辦')?.status, 'completed');
  await (await named(page, '已完成')).click();
  await waitNamed(page, '瀏覽器更新待辦');

  const restore = await visibleCandidate(
    [page.getByLabel('恢復待辦', { exact: true })],
    { last: true },
  );
  await restore.click();
  assert.equal(taskByTitle('瀏覽器更新待辦')?.status, 'pending');
  await (await named(page, '進行中')).click();
  await waitNamed(page, '瀏覽器更新待辦');
  record('complete_restore');

  await (await named(page, '待辦選項', { last: true })).click();
  await (await named(page, '刪除')).click();
  await waitNamed(page, '刪除待辦？');
  await (await named(page, '刪除')).click();
  await waitNamed(page, '待辦已刪除');
  await waitNamed(page, '瀏覽器更新待辦', false);
  assert.equal(observed.taskDelete.length, 1);
  record('delete_confirmation');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await enableFlutterSemantics(page);
  await waitNamed(page, '待辦');
  await waitNamed(page, '首頁');
  await waitNamed(page, '日曆');
  await waitNamed(page, '專案');
  await waitNamed(page, '更多');
  await named(page, '新增待辦');
  record('compact_runtime');

  await page.close();
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  serviceWorkers: 'block',
  locale: 'zh-TW',
  timezoneId: 'Asia/Taipei',
});

try {
  await runDesktopAcceptance(context);
  console.log(
    JSON.stringify({
      acceptance: 'task_ui_production_artifact',
      status: 'PASS',
      backend_runtime: 'validated-by-cloud-run-workflow',
    }),
  );
} catch (error) {
  const pages = context.pages();
  const page = pages.at(-1);
  if (page) {
    await page.screenshot({
      path: '/tmp/task-ui-acceptance.png',
      fullPage: true,
    }).catch(() => {});
    const labels = await page
      .locator('[aria-label]')
      .evaluateAll((nodes) =>
        nodes
          .map((node) => node.getAttribute('aria-label'))
          .filter(Boolean)
          .slice(0, 160),
      )
      .catch(() => []);
    console.error(`task_ui_semantics=${JSON.stringify(labels)}`);
  }
  throw error;
} finally {
  await context.close();
  await browser.close();
}
