import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const baseUrl = process.env.BASE_URL;
if (!baseUrl) {
  throw new Error('BASE_URL is required');
}

let nextProject = 1;
const projects = [
  {
    id: 'project-active',
    name: '驗收進行中專案',
    summary: '正式 Project UI artifact 驗收',
    status: 'active',
    created_at: '2026-09-28T08:00:00Z',
    updated_at: '2026-09-29T08:00:00Z',
  },
  {
    id: 'project-archived',
    name: '驗收已封存專案',
    summary: '封存狀態篩選資料',
    status: 'archived',
    created_at: '2026-09-27T08:00:00Z',
    updated_at: '2026-09-28T08:00:00Z',
  },
];
const tasks = [
  {
    id: 'project-task-open',
    title: '驗收關聯待辦',
    status: 'pending',
    project_id: 'project-active',
    due_at: null,
  },
  {
    id: 'project-task-completed',
    title: '驗收已完成關聯待辦',
    status: 'completed',
    project_id: 'project-active',
    due_at: null,
  },
];

const observed = {
  projectCreate: null,
  projectUpdate: [],
  projectDelete: [],
  requestTrace: [],
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
      email: 'project-ui-acceptance@example.invalid',
      name: 'Project UI Acceptance',
    }),
  );

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const method = request.method();
    const { pathname } = new URL(request.url());
    observed.requestTrace.push({ method, pathname });

    if (pathname === '/api/v1/projects' && method === 'GET') {
      return fulfillJson(route, 200, projects);
    }
    if (pathname === '/api/v1/tasks' && method === 'GET') {
      return fulfillJson(route, 200, tasks);
    }
    if (pathname === '/api/v1/projects' && method === 'POST') {
      const body = bodyOf(request);
      observed.projectCreate = body;
      const project = {
        id: `project-browser-${nextProject++}`,
        name: body.name,
        summary: body.summary ?? null,
        status: body.status ?? 'active',
        created_at: '2026-09-29T10:00:00Z',
        updated_at: '2026-09-29T10:00:00Z',
      };
      projects.push(project);
      return fulfillJson(route, 201, project);
    }

    const projectItem = pathname.match(/^\/api\/v1\/projects\/([^/]+)$/);
    if (projectItem) {
      const projectId = decodeURIComponent(projectItem[1]);
      const index = projects.findIndex((project) => project.id === projectId);
      if (index < 0) {
        return fulfillJson(route, 404, { detail: 'Project not found' });
      }
      if (method === 'PATCH') {
        const body = bodyOf(request);
        projects[index] = {
          ...projects[index],
          ...body,
          updated_at: '2026-09-29T11:00:00Z',
        };
        observed.projectUpdate.push({ projectId, body });
        return fulfillJson(route, 200, projects[index]);
      }
      if (method === 'DELETE') {
        projects.splice(index, 1);
        observed.projectDelete.push(projectId);
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
    await placeholder.first().evaluate((element) => element.click());
  } else {
    const enable = page.getByLabel('Enable accessibility', { exact: true });
    if ((await enable.count()) > 0) {
      await enable.first().evaluate((element) => element.click());
    }
  }
  await page.waitForTimeout(300);
}

function exactPattern(text) {
  return new RegExp(`^${text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`);
}

function escapedPattern(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function pageDelay(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
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
    await pageDelay(150);
  }
  throw new Error('No visible matching semantics node found');
}

async function named(page, text, options = {}) {
  const pattern = options.exact === false ? new RegExp(text) : exactPattern(text);
  return visibleCandidate(
    [
      page.getByRole('button', { name: pattern }),
      page.getByRole('menuitem', { name: pattern }),
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
    const textboxes = page.getByRole('textbox');
    const count = await textboxes.count();
    let seen = 0;
    for (let i = 0; i < count; i += 1) {
      const candidate = textboxes.nth(i);
      if (await candidate.isVisible().catch(() => false)) {
        if (seen === fallbackIndex) return candidate;
        seen += 1;
      }
    }
    throw new Error(`Textbox not found: ${name}`);
  }
}

async function editorTextboxFromEnd(page, offsetFromEnd) {
  const textboxes = page.getByRole('textbox');
  const visible = [];
  for (let i = 0; i < (await textboxes.count()); i += 1) {
    const candidate = textboxes.nth(i);
    if (await candidate.isVisible().catch(() => false)) {
      visible.push(candidate);
    }
  }
  const index = visible.length - 1 - offsetFromEnd;
  if (index < 0) {
    throw new Error(`Project editor textbox not found at offset ${offsetFromEnd}`);
  }
  const candidate = visible[index];
  const info = await candidate
    .evaluate((element) => ({
      role: element.getAttribute('role'),
      aria: element.getAttribute('aria-label'),
      tag: element.tagName,
    }))
    .catch(() => null);
  console.log(
    `project_ui_editor_textbox=offset:${offsetFromEnd} ${JSON.stringify(info)}`,
  );
  return candidate;
}

async function typeFlutterText(locator, text, label) {
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    await locator.click();
    await pageDelay(180);
    await locator.press('Control+A').catch(() => {});
    await locator.press('Backspace').catch(() => {});
    await locator.pressSequentially('x', { delay: 20 }).catch(() => {});
    await locator.press('Backspace').catch(() => {});
    await pageDelay(100);
    await locator.pressSequentially(text, { delay: 15 });
    await locator.press('Tab');
    await pageDelay(150);
    const value = await locator.inputValue().catch(() => null);
    console.log(
      `project_ui_typed=${label} attempt=${attempt} value=${JSON.stringify(value)}`,
    );
    if (value === text) {
      return;
    }
    if (attempt < 3) {
      await pageDelay(250);
    }
  }
  const value = await locator.inputValue().catch(() => null);
  assert.equal(value, text, `${label} DOM value did not match typed text`);
}

async function projectCard(page, projectName) {
  const pattern = new RegExp(`^${escapedPattern(projectName)}(?:\\n|$)`);
  return visibleCandidate([page.getByLabel(pattern), page.getByText(pattern)]);
}

async function openProjectOptions(page, projectName) {
  const card = await projectCard(page, projectName);
  const box = await card.boundingBox();
  assert.ok(box, `Project card ${projectName} had no bounding box`);
  const x = box.x + box.width - 24;
  const y = box.y + 24;
  console.log(
    `project_ui_pointer=project_options project=${JSON.stringify(projectName)} x=${x.toFixed(1)} y=${y.toFixed(1)}`,
  );
  await page.mouse.click(x, y);
  await named(page, '編輯');
}

async function isNamedVisible(page, text) {
  const pattern = new RegExp(escapedPattern(text));
  for (const locator of [page.getByLabel(pattern), page.getByText(pattern)]) {
    for (let i = 0; i < (await locator.count()); i += 1) {
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

async function waitObserved(predicate, label, timeout = 5000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (predicate()) return;
    await pageDelay(100);
  }
  console.error(`project_ui_observed=${JSON.stringify(observed)}`);
  throw new Error(`Acceptance observation timed out: ${label}`);
}

function record(check) {
  console.log(`project_ui_check=${check}:PASS`);
}

async function runAcceptance(context) {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1280, height: 900 });
  await installApiMocks(page);
  await page.goto(`${baseUrl}/projects`, { waitUntil: 'domcontentloaded' });
  await enableFlutterSemantics(page);

  await waitNamed(page, '驗收進行中專案');
  await waitNamed(page, '正式 Project UI artifact 驗收');
  await waitNamed(page, '驗收關聯待辦');
  await waitNamed(page, '未完成待辦 1');
  await waitNamed(page, '驗收已封存專案', false);
  record('production_artifact_project_list');

  const search = await textbox(page, /搜尋專案、摘要或待辦/);
  await search.fill('驗收關聯待辦');
  await waitNamed(page, '驗收進行中專案');
  await search.fill('不存在的專案驗收字串');
  await waitNamed(page, '驗收進行中專案', false);
  await search.fill('');
  await waitNamed(page, '驗收進行中專案');
  record('search');

  await (await named(page, '已封存')).click();
  await waitNamed(page, '驗收已封存專案');
  await waitNamed(page, '驗收進行中專案', false);
  await (await named(page, '進行中')).click();
  await waitNamed(page, '驗收進行中專案');
  record('status_filters');

  await (await named(page, '新增專案')).click();
  const createName = await editorTextboxFromEnd(page, 2);
  const createSummary = await editorTextboxFromEnd(page, 1);
  await editorTextboxFromEnd(page, 0);
  await createName.fill('瀏覽器新增專案');
  await typeFlutterText(createSummary, 'Project production acceptance', 'create_summary');
  await (await named(page, '儲存')).click();
  await waitObserved(
    () => observed.projectCreate?.name === '瀏覽器新增專案',
    'Project POST was not observed',
  );
  await waitNamed(page, '專案已新增');
  await waitNamed(page, '瀏覽器新增專案');
  assert.equal(observed.projectCreate?.summary, 'Project production acceptance');
  assert.equal(observed.projectCreate?.status, 'active');
  record('create');

  await page.waitForTimeout(4200);
  const createdCard = await projectCard(page, '瀏覽器新增專案');
  await createdCard.click();
  await waitNamed(page, '編輯專案');
  const editName = await editorTextboxFromEnd(page, 2);
  await editName.fill('瀏覽器更新專案');
  await (await named(page, '儲存')).click();
  await waitObserved(
    () => observed.projectUpdate.some(({ body }) => body.name === '瀏覽器更新專案'),
    'Project PATCH was not observed',
  );
  await waitNamed(page, '專案已更新');
  await waitNamed(page, '瀏覽器更新專案');
  record('edit');

  await page.waitForTimeout(4200);
  await openProjectOptions(page, '瀏覽器更新專案');
  await (await named(page, '刪除')).click();
  await waitNamed(page, '刪除專案？');
  record('delete_confirmation_present');
  console.log('project_ui_layered_check=delete_action_and_guard:validated-by-flutter-widget-tests');
  await page.keyboard.press('Escape');
  await waitNamed(page, '刪除專案？', false);
  assert.equal(observed.projectDelete.length, 0);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await enableFlutterSemantics(page);
  await waitNamed(page, '專案');
  await waitNamed(page, '首頁');
  await waitNamed(page, '待辦');
  await waitNamed(page, '日曆');
  await waitNamed(page, '更多');
  await named(page, '新增專案');
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
  await runAcceptance(context);
  console.log(
    JSON.stringify({
      acceptance: 'project_ui_production_artifact',
      status: 'PASS',
      destructive_actions: 'validated-by-flutter-widget-tests',
      backend_runtime: 'validated-by-cloud-run-workflow',
    }),
  );
} catch (error) {
  console.error(`project_ui_observed=${JSON.stringify(observed)}`);
  const page = context.pages().at(-1);
  if (page) {
    await page.screenshot({
      path: '/tmp/project-ui-acceptance.png',
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
    console.error(`project_ui_semantics=${JSON.stringify(labels)}`);
  }
  throw error;
} finally {
  await context.close();
  await browser.close();
}
