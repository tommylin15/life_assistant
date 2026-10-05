import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const baseUrl = process.env.BASE_URL;
if (!baseUrl) throw new Error('BASE_URL is required');

const document = {
  id: 'drive-production-document',
  google_file_id: 'picker-selected-production-file',
  name: 'Picker 驗收文件',
  mime_type: 'application/vnd.google-apps.document',
  web_view_link: 'https://drive.google.com/file/d/production-source/view',
  modified_at: '2026-10-04T08:00:00Z',
  created_at: '2026-10-04T08:00:00Z',
  updated_at: '2026-10-04T08:00:00Z',
};
const note = {
  id: 'drive-production-note',
  title: '既有驗收筆記',
  body: 'Drive Knowledge production artifact acceptance',
  project_id: null,
  created_at: '2026-10-04T08:00:00Z',
  updated_at: '2026-10-04T08:00:00Z',
};
const project = {
  id: 'drive-production-project',
  name: 'Drive 驗收專案',
};

const observed = {
  importBody: null,
  manualLink: null,
  sourceOpen: null,
};

function json(route, status, payload) {
  return route.fulfill({
    status,
    contentType: 'application/json; charset=utf-8',
    body: JSON.stringify(payload),
  });
}

function bodyOf(request) {
  const raw = request.postData();
  return raw ? JSON.parse(raw) : {};
}

async function installMocks(page) {
  await page.route('**/auth/me', (route) =>
    json(route, 200, {
      email: 'drive-production-ui@example.invalid',
      name: 'Drive Production UI Acceptance',
    }),
  );

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const method = request.method();
    const { pathname } = new URL(request.url());

    if (pathname === '/api/v1/drive/documents' && method === 'GET') {
      return json(route, 200, { documents: [document], returned: 1 });
    }
    if (pathname === '/api/v1/drive/enrichment/settings' && method === 'GET') {
      return json(route, 200, {
        auto_tags_enabled: true,
        note_suggestions_enabled: true,
        allow_document_content: true,
        max_related_note_suggestions: 5,
      });
    }
    if (
      pathname === `/api/v1/drive/documents/${document.id}/enrichment` &&
      method === 'GET'
    ) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json; charset=utf-8',
        body: 'null',
      });
    }
    if (pathname === '/api/v1/notes' && method === 'GET') {
      return json(route, 200, [note]);
    }
    if (pathname === '/api/v1/projects' && method === 'GET') {
      return json(route, 200, [project]);
    }
    if (
      pathname === `/api/v1/drive/documents/${document.id}/note-import` &&
      method === 'POST'
    ) {
      observed.importBody = bodyOf(request);
      return json(route, 201, {
        ...note,
        id: 'drive-imported-production-note',
        title: observed.importBody.title ?? document.name,
        project_id: observed.importBody.project_id ?? null,
      });
    }
    if (
      pathname === `/api/v1/drive/documents/${document.id}/notes/${note.id}` &&
      method === 'POST'
    ) {
      observed.manualLink = { documentId: document.id, noteId: note.id };
      return json(route, 200, {
        note,
        relation_type: 'related',
        link_source: 'manual',
      });
    }
    if (
      pathname === `/api/v1/drive/notes/${note.id}/documents` &&
      method === 'GET'
    ) {
      return json(route, 200, [
        {
          document,
          relation_type: 'source_import',
          link_source: 'import',
        },
        {
          document: {
            ...document,
            id: 'drive-related-production-document',
            name: '相關驗收文件',
            web_view_link: 'https://drive.google.com/file/d/related/view',
          },
          relation_type: 'related',
          link_source: 'manual',
        },
      ]);
    }
    if (
      pathname.startsWith('/api/v1/drive/notes/') &&
      pathname.endsWith('/documents') &&
      method === 'GET'
    ) {
      return json(route, 200, []);
    }

    console.error(`drive_knowledge_unexpected_api=${method} ${pathname}`);
    return json(route, 404, { detail: 'unexpected Drive Knowledge acceptance request' });
  });

  await page.route('https://drive.google.com/**', async (route) => {
    observed.sourceOpen = route.request().url();
    await route.abort();
  });
}

function installDiagnostics(page, label) {
  page.on('pageerror', (error) => {
    console.log(
      `drive_knowledge_page_error=${label}:${error.stack ?? error.message}`,
    );
  });
  page.on('console', (message) => {
    if (message.type() === 'error') {
      console.log(`drive_knowledge_console_error=${label}:${message.text()}`);
    }
  });
  page.on('requestfailed', (request) => {
    console.log(
      `drive_knowledge_request_failed=${label}:${request.failure()?.errorText ?? 'unknown'}:${request.url()}`,
    );
  });
}

async function enableFlutterSemantics(page) {
  const flutterView = page.locator('flutter-view');
  await flutterView.waitFor({ state: 'attached', timeout: 30000 });
  const rootVisible = await flutterView.first().isVisible().catch(() => false);
  console.log(`drive_knowledge_flutter_view=attached:visible=${rootVisible}`);

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

function escapeRegex(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function visible(locatorOrLocators, timeout = 15000) {
  const locators = Array.isArray(locatorOrLocators)
    ? locatorOrLocators
    : [locatorOrLocators];
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    for (const locator of locators) {
      const count = await locator.count();
      for (let index = 0; index < count; index += 1) {
        const item = locator.nth(index);
        if (await item.isVisible().catch(() => false)) return item;
      }
    }
    await pageDelay(120);
  }
  throw new Error('Visible semantics node not found');
}

async function named(page, text, { exact = true } = {}) {
  const pattern = exact
    ? new RegExp(`^${escapeRegex(text)}$`)
    : new RegExp(escapeRegex(text));
  for (const candidate of [
    page.getByRole('button', { name: pattern }),
    page.getByLabel(pattern),
    page.getByText(pattern),
  ]) {
    try {
      return await visible(candidate, 3500);
    } catch (_) {}
  }
  throw new Error(`Named UI not found: ${text}`);
}

async function pageDelay(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForText(page, text, timeout = 10000) {
  const pattern = new RegExp(escapeRegex(text));
  await visible(
    [page.getByLabel(pattern), page.getByText(pattern)],
    timeout,
  );
}

function record(check) {
  console.log(`drive_knowledge_ui_check=${check}:PASS`);
}

async function runAcceptance(context) {
  const page = await context.newPage();
  installDiagnostics(page, 'drive_knowledge');
  await page.setViewportSize({ width: 1280, height: 1000 });
  await installMocks(page);

  await page.goto(`${baseUrl}/more/drive`, { waitUntil: 'domcontentloaded' });
  await enableFlutterSemantics(page);
  await waitForText(page, document.name);
  await named(page, '轉成筆記');
  await named(page, '關聯既有筆記');
  record('drive_actions_rendered');

  await (await named(page, '轉成筆記')).click();
  await waitForText(page, '筆記標題');
  await waitForText(page, '標籤（逗號分隔）');
  await waitForText(page, '專案（選填）');
  record('import_dialog_contract');
  await page.keyboard.press('Escape');

  await (await named(page, '關聯既有筆記')).click();
  await (await named(page, '筆記')).click();
  await waitForText(page, note.title);
  record('manual_relation_dialog_contract');
  await page.keyboard.press('Escape');

  await page.goto(`${baseUrl}/more/notes`, { waitUntil: 'domcontentloaded' });
  await enableFlutterSemantics(page);
  await waitForText(page, note.title);
  await waitForText(page, `來源：Google Drive · ${document.name}`);
  await waitForText(page, '相關 Drive：相關驗收文件');
  record('note_reverse_discoverability');

  const sourceOpen = await named(page, '開啟原始文件');
  await sourceOpen.click();
  const deadline = Date.now() + 3000;
  while (!observed.sourceOpen && Date.now() < deadline) {
    await pageDelay(100);
  }
  assert.equal(observed.sourceOpen, document.web_view_link);
  record('source_link_returns_to_drive');

  console.log('drive_knowledge_ui_acceptance=PASS');
}

const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({
    serviceWorkers: 'block',
    locale: 'zh-TW',
    timezoneId: 'Asia/Taipei',
  });
  await runAcceptance(context);
  await context.close();
} catch (error) {
  console.error(`drive_knowledge_ui_acceptance=FAIL ${error?.stack ?? error}`);
  process.exitCode = 1;
} finally {
  await browser.close();
}
