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
    settings: {
      auto_tags_enabled: true,
      note_suggestions_enabled: true,
      allow_document_content: false,
      max_related_note_suggestions: 5,
    },
    run: {
      id: 'run-d1',
      drive_document_id: 'd1',
      content_fingerprint: 'fp-d1',
      provider: 'openai-should-not-render',
      model: 'vendor-model-should-not-render',
      status: 'partial',
      suggested_tags: ['旅行', '行程'],
      note_suggestions: [
        {
          id: 's1',
          note_id: 'n1',
          confidence: 0.91,
          reason: '內容與秋季旅行筆記高度相關',
          decision: 'pending',
          decided_at: null,
          created_at: '2026-10-03T00:00:00Z',
        },
      ],
      error_code: 'note_stage_failed',
      cache_hit: true,
      created_at: '2026-10-03T00:00:00Z',
    },
    decisions: [],
    reruns: [],
    settingsSaves: [],
  };
}

async function mockApi(page, state) {
  await page.route('**/auth/me', (route) =>
    json(route, 200, {
      email: 'drive-ui@example.invalid',
      name: 'Drive UI',
    }),
  );

  await page.route('**/api/v1/**', (route) => {
    const request = route.request();
    const method = request.method();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === '/api/v1/drive/documents' && method === 'GET') {
      return json(route, 200, {
        documents: [
          {
            id: 'd1',
            google_file_id: 'google-d1',
            name: '旅行規劃',
            mime_type: 'application/vnd.google-apps.document',
            web_view_link: 'https://drive.google.com/d1',
            modified_at: null,
            created_at: '2026-10-03T00:00:00Z',
            updated_at: '2026-10-03T00:00:00Z',
          },
        ],
      });
    }

    if (path === '/api/v1/notes' && method === 'GET') {
      return json(route, 200, [{ id: 'n1', title: '秋季旅行筆記' }]);
    }

    if (path === '/api/v1/drive/enrichment/settings' && method === 'GET') {
      return json(route, 200, state.settings);
    }

    if (path === '/api/v1/drive/enrichment/settings' && method === 'PUT') {
      const body = bodyOf(request);
      state.settingsSaves.push(body);
      state.settings = { ...state.settings, ...body };
      return json(route, 200, state.settings);
    }

    if (path === '/api/v1/drive/documents/d1/enrichment' && method === 'GET') {
      return json(route, 200, state.run);
    }

    if (path === '/api/v1/drive/documents/d1/enrichment' && method === 'POST') {
      const body = bodyOf(request);
      state.reruns.push(body);
      state.run = {
        ...state.run,
        status: 'succeeded',
        cache_hit: false,
      };
      return json(route, 200, state.run);
    }

    if (
      path === '/api/v1/drive/note-suggestions/s1/decision' &&
      method === 'POST'
    ) {
      const body = bodyOf(request);
      state.decisions.push(body);
      const suggestion = {
        ...state.run.note_suggestions[0],
        decision: body.decision,
        decided_at: '2026-10-03T01:00:00Z',
      };
      state.run = {
        ...state.run,
        note_suggestions: [suggestion],
      };
      return json(route, 200, suggestion);
    }

    return json(route, 404, { detail: `unexpected ${method} ${path}` });
  });
}

function installDiagnostics(page, label) {
  page.on('pageerror', (error) => {
    console.log(`drive_ui_page_error=${label}:${error.stack ?? error.message}`);
  });
  page.on('console', (message) => {
    if (message.type() === 'error') {
      console.log(`drive_ui_console_error=${label}:${message.text()}`);
    }
  });
  page.on('requestfailed', (request) => {
    console.log(
      `drive_ui_request_failed=${label}:${request.failure()?.errorText ?? 'unknown'}:${request.url()}`,
    );
  });
}

async function semantics(page, label) {
  const flutterView = page.locator('flutter-view');
  await flutterView.waitFor({ state: 'attached', timeout: 30000 });
  const rootVisible = await flutterView.first().isVisible().catch(() => false);
  console.log(`drive_ui_flutter_view=${label}:attached:visible=${rootVisible}`);

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
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function candidates(page, text) {
  const pattern = text instanceof RegExp ? text : new RegExp(`^${esc(text)}$`);
  const loosePattern = text instanceof RegExp ? text : new RegExp(esc(text));
  return [
    page.getByRole('button', { name: pattern }),
    page.getByRole('switch', { name: pattern }),
    page.getByRole('checkbox', { name: pattern }),
    page.getByRole('menuitem', { name: pattern }),
    page.getByLabel(pattern),
    page.getByText(pattern),
    page.getByLabel(loosePattern),
    page.getByText(loosePattern),
  ];
}

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
    await delay(120);
  }
  throw new Error('visible locator not found');
}

async function named(page, text, timeout = 12000) {
  return visible(candidates(page, text), timeout);
}

async function scrollNamed(page, text) {
  for (let attempt = 0; attempt < 8; attempt += 1) {
    try {
      return await named(page, text, 700);
    } catch (_) {
      await page.mouse.wheel(0, 420);
      await delay(180);
    }
  }
  throw new Error(`named not found after scrolling: ${text}`);
}

async function waitObserved(predicate, label) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (predicate()) return;
    await delay(100);
  }
  throw new Error(`not observed: ${label}`);
}

const pass = (name) => console.log(`drive_ui_check=${name}:PASS`);

async function desktop(context) {
  const page = await context.newPage();
  installDiagnostics(page, 'desktop');
  await page.setViewportSize({ width: 1280, height: 900 });
  const state = initialState();
  await mockApi(page, state);

  await page.goto(`${baseUrl}/more/drive`, { waitUntil: 'domcontentloaded' });
  await semantics(page, 'desktop_review');

  await named(page, 'Google Drive 智能整理');
  await named(page, /目前未允許將文件內容送交 AI 分析/);
  await scrollNamed(page, '旅行規劃');
  await scrollNamed(page, '部分完成');
  await scrollNamed(page, '使用快取');
  await scrollNamed(page, '秋季旅行筆記');
  assert.equal(
    await page.getByText('openai-should-not-render', { exact: true }).count(),
    0,
    'provider identity must not render',
  );
  assert.equal(
    await page.getByText('vendor-model-should-not-render', { exact: true }).count(),
    0,
    'model identity must not render',
  );
  pass('review_provider_neutral');

  await (await scrollNamed(page, '接受')).click();
  await waitObserved(
    () => state.decisions.some((entry) => entry.decision === 'accepted'),
    'accepted decision',
  );
  await scrollNamed(page, '已接受');
  pass('accept_suggestion');

  await (await scrollNamed(page, '重新分析')).click();
  await waitObserved(
    () => state.reruns.some((entry) => entry.force === true),
    'force rerun',
  );
  pass('force_reanalyze');

  await page.goto(`${baseUrl}/more/drive/settings`, {
    waitUntil: 'domcontentloaded',
  });
  await semantics(page, 'desktop_settings');
  await named(page, '智能整理設定');
  const consent = await scrollNamed(page, '允許將文件內容送交 AI 分析');
  await consent.click();
  await (await scrollNamed(page, '儲存設定')).click();
  await waitObserved(() => state.settingsSaves.length === 1, 'settings save');

  const saved = state.settingsSaves[0];
  assert.deepEqual(Object.keys(saved).sort(), [
    'allow_document_content',
    'auto_tags_enabled',
    'max_related_note_suggestions',
    'note_suggestions_enabled',
  ]);
  assert.equal(saved.allow_document_content, true);
  assert.equal(saved.auto_tags_enabled, true);
  assert.equal(saved.note_suggestions_enabled, true);
  assert.equal(saved.max_related_note_suggestions, 5);
  await scrollNamed(page, '設定已儲存');
  pass('settings_consent_save');

  await page.close();
}

async function mobile(context) {
  const page = await context.newPage();
  installDiagnostics(page, 'mobile');
  await page.setViewportSize({ width: 390, height: 844 });
  const state = initialState();
  await mockApi(page, state);

  await page.goto(`${baseUrl}/more/drive`, { waitUntil: 'domcontentloaded' });
  await semantics(page, 'mobile_review');
  await named(page, 'Google Drive 智能整理');
  await scrollNamed(page, '旅行規劃');
  await scrollNamed(page, '接受');
  await scrollNamed(page, '拒絕');
  pass('mobile_review_controls');

  await page.goto(`${baseUrl}/more/drive/settings`, {
    waitUntil: 'domcontentloaded',
  });
  await semantics(page, 'mobile_settings');
  await named(page, '智能整理設定');
  await scrollNamed(page, '允許將文件內容送交 AI 分析');
  await scrollNamed(page, '儲存設定');
  pass('mobile_settings');

  await page.screenshot({
    path: '/tmp/drive-ui-acceptance.png',
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
  console.log('drive_ui_acceptance=PASS');
} finally {
  await browser.close();
}
