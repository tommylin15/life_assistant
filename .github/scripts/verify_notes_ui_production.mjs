import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const baseUrl = process.env.BASE_URL;
if (!baseUrl) throw new Error('BASE_URL is required');

const projects = [{ id: 'p-travel', name: '旅行專案' }];
let notes = [
  {
    id: 'note-primary',
    title: '驗收主筆記',
    body: '# 驗收內容\n正式 Notes UI artifact',
    project_id: 'p-travel',
    created_at: '2026-09-29T08:00:00Z',
    updated_at: '2026-09-30T08:00:00Z',
  },
  {
    id: 'note-target',
    title: '驗收被連結筆記',
    body: '雙向連結 target',
    project_id: null,
    created_at: '2026-09-29T07:00:00Z',
    updated_at: '2026-09-29T09:00:00Z',
  },
];
const tags = new Map([['note-primary', ['既有標籤']]]);
const links = new Map();
let nextNote = 1;
const observed = {
  search: [],
  create: null,
  tags: [],
  links: [],
  unlinks: [],
  deletes: [],
};

const json = (route, status, body) =>
  route.fulfill({
    status,
    contentType: 'application/json; charset=utf-8',
    body: JSON.stringify(body),
  });
const bodyOf = (request) =>
  request.postData() ? JSON.parse(request.postData()) : {};

function addLink(a, b) {
  if (!links.has(a)) links.set(a, new Set());
  if (!links.has(b)) links.set(b, new Set());
  links.get(a).add(b);
  links.get(b).add(a);
}

function removeLink(a, b) {
  links.get(a)?.delete(b);
  links.get(b)?.delete(a);
}

async function mockApi(page) {
  await page.route('**/auth/me', (route) =>
    json(route, 200, {
      email: 'notes-ui@example.invalid',
      name: 'Notes UI',
    }),
  );
  await page.route('**/api/v1/**', (route) => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === '/api/v1/projects' && method === 'GET') {
      return json(route, 200, projects);
    }
    if (path === '/api/v1/notes' && method === 'GET') {
      const q = (url.searchParams.get('q') ?? '').trim();
      observed.search.push(q);
      const needle = q.toLowerCase();
      return json(
        route,
        200,
        needle
          ? notes.filter((note) =>
              `${note.title}\n${note.body}`.toLowerCase().includes(needle),
            )
          : notes,
      );
    }
    if (path === '/api/v1/notes' && method === 'POST') {
      const body = bodyOf(request);
      observed.create = body;
      const note = {
        id: `note-browser-${nextNote++}`,
        created_at: '2026-09-30T09:00:00Z',
        updated_at: '2026-09-30T09:00:00Z',
        ...body,
      };
      notes = [note, ...notes];
      return json(route, 201, note);
    }

    let match = path.match(/^\/api\/v1\/notes\/([^/]+)\/tags$/);
    if (match) {
      const id = decodeURIComponent(match[1]);
      if (method === 'GET') {
        return json(route, 200, { tags: tags.get(id) ?? [] });
      }
      if (method === 'PUT') {
        const values = bodyOf(request).tags ?? [];
        tags.set(id, [...values]);
        observed.tags.push({ id, values: [...values] });
        return json(route, 200, { tags: values });
      }
    }

    match = path.match(/^\/api\/v1\/notes\/([^/]+)\/links\/([^/]+)$/);
    if (match && method === 'DELETE') {
      const id = decodeURIComponent(match[1]);
      const target = decodeURIComponent(match[2]);
      removeLink(id, target);
      observed.unlinks.push({ id, target });
      return route.fulfill({ status: 204, body: '' });
    }

    match = path.match(/^\/api\/v1\/notes\/([^/]+)\/links$/);
    if (match) {
      const id = decodeURIComponent(match[1]);
      if (method === 'GET') {
        return json(
          route,
          200,
          notes.filter((note) => (links.get(id) ?? new Set()).has(note.id)),
        );
      }
      if (method === 'POST') {
        const target = bodyOf(request).target_note_id;
        addLink(id, target);
        observed.links.push({ id, target });
        return route.fulfill({ status: 204, body: '' });
      }
    }

    match = path.match(/^\/api\/v1\/notes\/([^/]+)$/);
    if (match) {
      const id = decodeURIComponent(match[1]);
      const index = notes.findIndex((note) => note.id === id);
      if (method === 'PATCH') {
        notes[index] = {
          ...notes[index],
          ...bodyOf(request),
          updated_at: '2026-09-30T10:00:00Z',
        };
        return json(route, 200, notes[index]);
      }
      if (method === 'DELETE') {
        const confirmation =
          request.headers()['x-life-assistant-confirmation'] ?? '';
        observed.deletes.push({ id, confirmation });
        notes.splice(index, 1);
        return route.fulfill({ status: 204, body: '' });
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

const esc = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const pageDelay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function visible(locators, timeout = 12000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    for (const locator of locators) {
      for (let index = 0; index < (await locator.count()); index += 1) {
        if (await locator.nth(index).isVisible().catch(() => false)) {
          return locator.nth(index);
        }
      }
    }
    await pageDelay(120);
  }
  throw new Error('visible locator not found');
}

async function named(page, text, { last = false } = {}) {
  const pattern =
    text instanceof RegExp ? text : new RegExp(`^${esc(text)}$`);
  const candidates = [
    page.getByRole('button', { name: pattern }),
    page.getByRole('menuitem', { name: pattern }),
    page.getByRole('option', { name: pattern }),
    page.getByLabel(pattern),
    page.getByText(pattern),
  ];
  if (!last) return visible(candidates);
  for (const locator of candidates) {
    const count = await locator.count();
    for (let index = count - 1; index >= 0; index -= 1) {
      if (await locator.nth(index).isVisible().catch(() => false)) {
        return locator.nth(index);
      }
    }
  }
  throw new Error(`named not found: ${text}`);
}

async function textbox(page, label, fallbackIndex = 0) {
  const pattern = label instanceof RegExp ? label : new RegExp(esc(label));
  try {
    return await visible(
      [
        page.getByRole('textbox', { name: pattern }),
        page.getByLabel(pattern),
      ],
      3000,
    );
  } catch (_) {
    const textboxes = page.getByRole('textbox');
    const count = await textboxes.count();
    let seen = 0;
    for (let index = 0; index < count; index += 1) {
      const candidate = textboxes.nth(index);
      if (await candidate.isVisible().catch(() => false)) {
        if (seen === fallbackIndex) return candidate;
        seen += 1;
      }
    }
    throw new Error(`Textbox not found: ${label}`);
  }
}

async function editorTextboxFromEnd(page, offsetFromEnd, timeout = 5000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const textboxes = page.getByRole('textbox');
    const visibleTextboxes = [];
    for (let index = 0; index < (await textboxes.count()); index += 1) {
      const candidate = textboxes.nth(index);
      if (await candidate.isVisible().catch(() => false)) {
        visibleTextboxes.push(candidate);
      }
    }
    const index = visibleTextboxes.length - 1 - offsetFromEnd;
    if (index >= 0) {
      const candidate = visibleTextboxes[index];
      const info = await candidate
        .evaluate((element) => ({
          tag: element.tagName,
          role: element.getAttribute('role'),
          aria: element.getAttribute('aria-label'),
        }))
        .catch(() => null);
      console.log(
        `notes_ui_editor_textbox=offset:${offsetFromEnd} ${JSON.stringify(info)}`,
      );
      return candidate;
    }
    await pageDelay(120);
  }
  throw new Error(`Notes editor textbox not found at offset ${offsetFromEnd}`);
}

async function fillVerified(locator, value, label) {
  await locator.fill(value);
  const actual = await locator.inputValue();
  console.log(`notes_ui_editor_value=${label} ${JSON.stringify(actual)}`);
  assert.equal(actual, value, `${label} DOM value did not match filled value`);
}

async function waitObserved(predicate, label) {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    if (predicate()) return;
    await pageDelay(100);
  }
  throw new Error(`not observed: ${label}`);
}

const pass = (name) => console.log(`notes_ui_check=${name}:PASS`);
const stage = (name) => console.log(`notes_ui_stage=${name}`);

async function desktop(context) {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1280, height: 900 });
  await mockApi(page);
  await page.goto(`${baseUrl}/more/notes`, { waitUntil: 'domcontentloaded' });
  await semantics(page);
  stage('list_note');
  await named(page, /驗收主筆記/);
  stage('list_project');
  await named(page, /旅行專案/);
  pass('list');

  const search = await textbox(page, /搜尋筆記標題或內容/);
  await search.fill('正式 Notes UI artifact');
  await (await named(page, '搜尋')).click();
  await waitObserved(
    () => observed.search.at(-1) === '正式 Notes UI artifact',
    'search query',
  );
  pass('server_search');
  const resetSearch = await textbox(page, /搜尋筆記標題或內容/);
  await resetSearch.fill('');
  await (await named(page, '搜尋')).click();
  await named(page, /驗收被連結筆記/);

  await (await named(page, '新增筆記')).click();
  const editorTitle = await editorTextboxFromEnd(page, 2);
  const editorTags = await editorTextboxFromEnd(page, 1);
  const editorBody = await editorTextboxFromEnd(page, 0);
  const expectedBody = '# 瀏覽器 Markdown\n**正式驗收**';
  await fillVerified(editorTitle, '瀏覽器新增筆記', 'title');
  await fillVerified(editorTags, '驗收, Markdown, 驗收', 'tags');
  await editorBody.fill(expectedBody);
  console.log('notes_ui_editor_value=body verified_by=markdown_preview_and_create_payload');
  await (await named(page, '預覽')).click();
  await named(page, /瀏覽器 Markdown/);
  await named(page, /正式驗收/);
  pass('markdown_preview');
  await (await named(page, '儲存')).click();
  await waitObserved(
    () => observed.create?.title === '瀏覽器新增筆記',
    'create',
  );
  assert.equal(
    observed.create?.body,
    expectedBody,
    'created note body did not match the editor body',
  );
  await waitObserved(
    () => observed.tags.some((entry) => entry.values.join('|') === '驗收|Markdown'),
    'tags',
  );
  await named(page, /筆記已新增/);
  pass('create_tags');

  await pageDelay(4200);
  await (await named(page, '筆記選項')).click();
  await (await named(page, '雙向連結')).click();
  const selector = await named(page, /連結另一則筆記/);
  await selector.click();
  await (await named(page, /驗收被連結筆記/, { last: true })).click();
  await (await named(page, '新增雙向連結')).click();
  const created = notes.find((note) => note.title === '瀏覽器新增筆記');
  assert.ok(created);
  await waitObserved(
    () =>
      observed.links.some(
        (entry) => entry.id === created.id && entry.target === 'note-target',
      ),
    'link',
  );
  pass('link');
  await (await named(page, /移除與 驗收被連結筆記 的連結/)).click();
  await waitObserved(
    () =>
      observed.unlinks.some(
        (entry) => entry.id === created.id && entry.target === 'note-target',
      ),
    'unlink',
  );
  pass('unlink');
  await (await named(page, '關閉')).click();

  await (await named(page, '筆記選項')).click();
  await (await named(page, '刪除')).click();
  await named(page, /刪除筆記？/);
  await (await named(page, '刪除', { last: true })).click();
  await waitObserved(
    () => observed.deletes.some((entry) => entry.id === created.id),
    'delete',
  );
  assert.equal(
    observed.deletes.find((entry) => entry.id === created.id).confirmation,
    `explicit_user:note.delete:${created.id}`,
  );
  pass('delete_confirmation');
  await page.close();
}

async function mobile(context) {
  const page = await context.newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  await mockApi(page);
  const overflow = [];
  page.on('console', (message) => {
    if (/RenderFlex overflowed|overflowed by/i.test(message.text())) {
      overflow.push(message.text());
    }
  });
  await page.goto(`${baseUrl}/more/notes`, { waitUntil: 'domcontentloaded' });
  await semantics(page);
  await named(page, /驗收主筆記/);
  await (await named(page, '新增筆記')).click();
  await editorTextboxFromEnd(page, 2);
  await editorTextboxFromEnd(page, 0);
  assert.deepEqual(overflow, []);
  pass('mobile_editor');
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
  console.log('notes_ui_acceptance=PASS');
} catch (error) {
  console.error(error);
  try {
    const page = browser.contexts().flatMap((context) => context.pages()).at(-1);
    if (page) {
      await page.screenshot({
        path: '/tmp/notes-ui-acceptance.png',
        fullPage: true,
      });
    }
  } catch (_) {}
  process.exitCode = 1;
} finally {
  await browser.close();
}
