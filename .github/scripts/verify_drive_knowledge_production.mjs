import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const baseUrl = process.env.DRIVE_UI_BASE_URL;
if (!baseUrl) {
  console.error('DRIVE_UI_BASE_URL is required');
  process.exit(2);
}

const document = {
  id: 'acceptance-drive-document',
  google_file_id: 'acceptance-google-file',
  name: '驗收 Drive 文件',
  mime_type: 'application/vnd.google-apps.document',
  web_view_link: 'https://drive.google.com/file/d/acceptance-google-file/view',
  modified_at: '2026-10-05T00:00:00Z',
  created_at: '2026-10-05T00:00:00Z',
  updated_at: '2026-10-05T00:00:00Z',
};
const note = {
  id: 'acceptance-note',
  title: '既有驗收筆記',
  body: 'acceptance note body',
  project_id: null,
  created_at: '2026-10-05T00:00:00Z',
  updated_at: '2026-10-05T00:00:00Z',
};
const project = {
  id: 'acceptance-project',
  name: '驗收專案',
  description: '',
  status: 'active',
  created_at: '2026-10-05T00:00:00Z',
  updated_at: '2026-10-05T00:00:00Z',
};

const observed = {
  importBody: null,
  linkBody: null,
  sourceOpen: null,
};

function json(route, payload, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(payload),
  });
}

function installDiagnostics(page, label) {
  page.on('pageerror', (error) => {
    console.error(`${label}_pageerror=${error?.stack ?? error}`);
  });
  page.on('console', (message) => {
    if (message.type() === 'error') {
      console.error(`${label}_console_error=${message.text()}`);
    }
  });
  page.on('requestfailed', (request) => {
    console.error(
      `${label}_requestfailed=${request.method()} ${request.url()} ${request.failure()?.errorText ?? 'unknown'}`,
    );
  });
}

async function installMocks(page) {
  await page.route('**/auth/me', (route) =>
    json(route, {
      id: 'acceptance-user',
      email: 'acceptance@example.invalid',
      name: 'Acceptance User',
      picture: null,
    }),
  );

  await page.route('**/api/v1/drive/documents', (route) => {
    if (route.request().method() === 'GET') return json(route, [document]);
    return route.fallback();
  });

  await page.route('**/api/v1/drive/enrichment/settings', (route) =>
    json(route, {
      auto_tags_enabled: true,
      note_suggestions_enabled: true,
      allow_document_content: true,
      max_related_note_suggestions: 5,
    }),
  );

  await page.route('**/api/v1/drive/documents/*/enrichment', (route) =>
    json(route, null),
  );

  await page.route('**/api/v1/notes', (route) => {
    if (route.request().method() === 'GET') return json(route, [note]);
    return route.fallback();
  });

  await page.route('**/api/v1/projects', (route) => {
    if (route.request().method() === 'GET') return json(route, [project]);
    return route.fallback();
  });

  await page.route('**/api/v1/drive/documents/*/note-import', async (route) => {
    observed.importBody = route.request().postDataJSON();
    return json(route, note, 201);
  });

  await page.route('**/api/v1/drive/documents/*/notes/*', async (route) => {
    if (route.request().method() === 'POST') {
      observed.linkBody = {
        documentId: route.request().url().split('/documents/')[1].split('/notes/')[0],
        noteId: route.request().url().split('/notes/')[1].split(/[?#]/)[0],
      };
      return json(route, {
        note,
        relation_type: 'related',
        link_source: 'manual',
      });
    }
    return route.fallback();
  });

  await page.route(`**/api/v1/drive/notes/${note.id}/documents`, (route) =>
    json(route, [
      {
        document,
        relation_type: 'source_import',
        link_source: 'import',
      },
      {
        document: {
          ...document,
          id: 'acceptance-related-drive-document',
          google_file_id: 'acceptance-related-google-file',
          name: '相關驗收文件',
          web_view_link: 'https://drive.google.com/file/d/acceptance-related-google-file/view',
        },
        relation_type: 'related',
        link_source: 'manual',
      },
    ]),
  );

  await page.route('**/api/v1/drive/notes/*/documents', (route) => json(route, []));

  await page.route('https://drive.google.com/**', async (route) => {
    observed.sourceOpen = route.request().url();
    await route.abort();
  });

  await page.route('**/api/v1/**', (route) => {
    console.error(
      `drive_knowledge_unexpected_api=${route.request().method()} ${route.request().url()}`,
    );
    return route.fallback();
  });
}

async function enableFlutterSemantics(page) {
  await page.locator('flutter-view').waitFor({ state: 'attached', timeout: 30000 });
  const flutterView = page.locator('flutter-view').first();
  console.log(`drive_knowledge_flutter_view=attached:visible=${await flutterView.isVisible().catch(() => false)}`);
  const enable = page.getByLabel('Enable accessibility', { exact: true });
  if ((await enable.count()) > 0) {
    await enable.first().evaluate((element) => element.click());
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
    locale: 'zh-TW',
    timezoneId: 'Asia/Taipei',
    serviceWorkers: 'block',
  });
  await runAcceptance(context);
  await context.close();
} finally {
  await browser.close();
}
