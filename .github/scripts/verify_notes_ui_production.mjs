import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const baseUrl = process.env.BASE_URL;
if (!baseUrl) throw new Error('BASE_URL is required');

const projects = [{ id: 'p-travel', name: '旅行專案' }];
let notes = [
  { id: 'note-primary', title: '驗收主筆記', body: '# 驗收內容\n正式 Notes UI artifact', project_id: 'p-travel', created_at: '2026-09-29T08:00:00Z', updated_at: '2026-09-30T08:00:00Z' },
  { id: 'note-target', title: '驗收被連結筆記', body: '雙向連結 target', project_id: null, created_at: '2026-09-29T07:00:00Z', updated_at: '2026-09-29T09:00:00Z' },
];
const tags = new Map([['note-primary', ['既有標籤']]]);
const links = new Map();
let nextNote = 1;
const observed = { search: [], create: null, tags: [], links: [], unlinks: [], deletes: [] };

const json = (route, status, body) => route.fulfill({ status, contentType: 'application/json; charset=utf-8', body: JSON.stringify(body) });
const bodyOf = (request) => request.postData() ? JSON.parse(request.postData()) : {};

function addLink(a, b) {
  if (!links.has(a)) links.set(a, new Set());
  if (!links.has(b)) links.set(b, new Set());
  links.get(a).add(b); links.get(b).add(a);
}
function removeLink(a, b) { links.get(a)?.delete(b); links.get(b)?.delete(a); }

async function mockApi(page) {
  await page.route('**/auth/me', (route) => json(route, 200, { email: 'notes-ui@example.invalid', name: 'Notes UI' }));
  await page.route('**/api/v1/**', (route) => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;
    if (path === '/api/v1/projects' && method === 'GET') return json(route, 200, projects);
    if (path === '/api/v1/notes' && method === 'GET') {
      const q = (url.searchParams.get('q') ?? '').trim();
      observed.search.push(q);
      const needle = q.toLowerCase();
      return json(route, 200, needle ? notes.filter((n) => `${n.title}\n${n.body}`.toLowerCase().includes(needle)) : notes);
    }
    if (path === '/api/v1/notes' && method === 'POST') {
      const body = bodyOf(request);
      observed.create = body;
      const note = { id: `note-browser-${nextNote++}`, created_at: '2026-09-30T09:00:00Z', updated_at: '2026-09-30T09:00:00Z', ...body };
      notes = [note, ...notes];
      return json(route, 201, note);
    }
    let match = path.match(/^\/api\/v1\/notes\/([^/]+)\/tags$/);
    if (match) {
      const id = decodeURIComponent(match[1]);
      if (method === 'GET') return json(route, 200, { tags: tags.get(id) ?? [] });
      if (method === 'PUT') {
        const values = bodyOf(request).tags ?? [];
        tags.set(id, [...values]); observed.tags.push({ id, values: [...values] });
        return json(route, 200, { tags: values });
      }
    }
    match = path.match(/^\/api\/v1\/notes\/([^/]+)\/links\/([^/]+)$/);
    if (match && method === 'DELETE') {
      const id = decodeURIComponent(match[1]); const target = decodeURIComponent(match[2]);
      removeLink(id, target); observed.unlinks.push({ id, target });
      return route.fulfill({ status: 204, body: '' });
    }
    match = path.match(/^\/api\/v1\/notes\/([^/]+)\/links$/);
    if (match) {
      const id = decodeURIComponent(match[1]);
      if (method === 'GET') return json(route, 200, notes.filter((n) => (links.get(id) ?? new Set()).has(n.id)));
      if (method === 'POST') {
        const target = bodyOf(request).target_note_id; addLink(id, target); observed.links.push({ id, target });
        return route.fulfill({ status: 204, body: '' });
      }
    }
    match = path.match(/^\/api\/v1\/notes\/([^/]+)$/);
    if (match) {
      const id = decodeURIComponent(match[1]); const index = notes.findIndex((n) => n.id === id);
      if (method === 'PATCH') { notes[index] = { ...notes[index], ...bodyOf(request), updated_at: '2026-09-30T10:00:00Z' }; return json(route, 200, notes[index]); }
      if (method === 'DELETE') {
        const confirmation = request.headers()['x-life-assistant-confirmation'] ?? '';
        observed.deletes.push({ id, confirmation }); notes.splice(index, 1); return route.fulfill({ status: 204, body: '' });
      }
    }
    return json(route, 404, { detail: `unexpected ${method} ${path}` });
  });
}

async function semantics(page) {
  await page.waitForSelector('flutter-view', { timeout: 30000 });
  const placeholder = page.locator('flt-semantics-placeholder');
  if (await placeholder.count()) await placeholder.first().evaluate((e) => e.click());
  await page.waitForTimeout(300);
}

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const pageDelay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function visible(locators, timeout = 12000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    for (const locator of locators) for (let i = 0; i < await locator.count(); i += 1) if (await locator.nth(i).isVisible().catch(() => false)) return locator.nth(i);
    await pageDelay(120);
  }
  throw new Error('visible locator not found');
}
async function named(page, text, { last = false } = {}) {
  const pattern = text instanceof RegExp ? text : new RegExp(`^${esc(text)}$`);
  const candidates = [page.getByRole('button', { name: pattern }), page.getByRole('menuitem', { name: pattern }), page.getByRole('option', { name: pattern }), page.getByLabel(pattern), page.getByText(pattern)];
  if (!last) return visible(candidates);
  for (const locator of candidates) {
    const count = await locator.count();
    for (let i = count - 1; i >= 0; i -= 1) if (await locator.nth(i).isVisible().catch(() => false)) return locator.nth(i);
  }
  throw new Error(`named not found: ${text}`);
}
async function textbox(page, label) { const p = label instanceof RegExp ? label : new RegExp(esc(label)); return visible([page.getByRole('textbox', { name: p }), page.getByLabel(p)]); }
async function waitObserved(fn, label) { for (let i = 0; i < 50; i += 1) { if (fn()) return; await pageDelay(100); } throw new Error(`not observed: ${label}`); }
const pass = (name) => console.log(`notes_ui_check=${name}:PASS`);

async function desktop(context) {
  const page = await context.newPage();
  await page.setViewportSize({ width: 1280, height: 900 }); await mockApi(page);
  await page.goto(`${baseUrl}/more/notes`, { waitUntil: 'domcontentloaded' }); await semantics(page);
  await named(page, '驗收主筆記'); await named(page, '旅行專案'); pass('list');

  const search = await textbox(page, /搜尋筆記標題或內容/); await search.fill('正式 Notes UI artifact'); await (await named(page, '搜尋')).click();
  await waitObserved(() => observed.search.at(-1) === '正式 Notes UI artifact', 'search query'); pass('server_search');
  await search.fill(''); await (await named(page, '搜尋')).click(); await named(page, '驗收被連結筆記');

  await (await named(page, '新增筆記')).click();
  await (await textbox(page, /標題/)).fill('瀏覽器新增筆記');
  await (await textbox(page, /標籤/)).fill('驗收, Markdown, 驗收');
  await (await textbox(page, /Markdown 內容/)).fill('# 瀏覽器 Markdown\n**正式驗收**');
  await (await named(page, '預覽')).click(); await named(page, '瀏覽器 Markdown'); pass('markdown_preview');
  await (await named(page, '儲存')).click();
  await waitObserved(() => observed.create?.title === '瀏覽器新增筆記', 'create');
  await waitObserved(() => observed.tags.some((x) => x.values.join('|') === '驗收|Markdown'), 'tags');
  await named(page, '筆記已新增'); pass('create_tags');

  await pageDelay(4200); await (await named(page, '筆記選項')).click(); await (await named(page, '雙向連結')).click();
  const selector = await named(page, /連結另一則筆記/); await selector.click(); await (await named(page, '驗收被連結筆記', { last: true })).click();
  await (await named(page, '新增雙向連結')).click();
  const created = notes.find((n) => n.title === '瀏覽器新增筆記'); assert.ok(created);
  await waitObserved(() => observed.links.some((x) => x.id === created.id && x.target === 'note-target'), 'link'); pass('link');
  await (await named(page, /移除與 驗收被連結筆記 的連結/)).click();
  await waitObserved(() => observed.unlinks.some((x) => x.id === created.id && x.target === 'note-target'), 'unlink'); pass('unlink');
  await (await named(page, '關閉')).click();

  await (await named(page, '筆記選項')).click(); await (await named(page, '刪除')).click(); await named(page, '刪除筆記？'); await (await named(page, '刪除', { last: true })).click();
  await waitObserved(() => observed.deletes.some((x) => x.id === created.id), 'delete');
  assert.equal(observed.deletes.find((x) => x.id === created.id).confirmation, `explicit_user:note.delete:${created.id}`); pass('delete_confirmation');
  await page.close();
}

async function mobile(context) {
  const page = await context.newPage(); await page.setViewportSize({ width: 390, height: 844 }); await mockApi(page);
  const overflow = []; page.on('console', (m) => { if (/RenderFlex overflowed|overflowed by/i.test(m.text())) overflow.push(m.text()); });
  await page.goto(`${baseUrl}/more/notes`, { waitUntil: 'domcontentloaded' }); await semantics(page); await named(page, '驗收主筆記');
  await (await named(page, '新增筆記')).click(); await textbox(page, /標題/); await textbox(page, /Markdown 內容/);
  assert.deepEqual(overflow, []); pass('mobile_editor'); await page.close();
}

const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext(); await desktop(context); await mobile(context); console.log('notes_ui_acceptance=PASS');
} catch (error) {
  console.error(error);
  try { const page = browser.contexts().flatMap((c) => c.pages()).at(-1); if (page) await page.screenshot({ path: '/tmp/notes-ui-acceptance.png', fullPage: true }); } catch (_) {}
  process.exitCode = 1;
} finally { await browser.close(); }
