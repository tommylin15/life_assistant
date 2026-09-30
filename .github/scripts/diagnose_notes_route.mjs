import { chromium } from 'playwright';

const baseUrl = process.env.BASE_URL;
if (!baseUrl) throw new Error('BASE_URL is required');

async function inspectRoute(context, path) {
  const page = await context.newPage();
  const label = path.replaceAll('/', '_') || '_root';
  page.on('console', (message) => {
    console.log(`notes_route_console=${label}:${message.type()}:${message.text()}`);
  });
  page.on('pageerror', (error) => {
    console.error(`notes_route_pageerror=${label}:${error.stack ?? error.message}`);
  });
  page.on('requestfailed', (request) => {
    console.error(
      `notes_route_request_failed=${label}:${request.method()}:${request.url()}:${request.failure()?.errorText ?? 'unknown'}`,
    );
  });
  page.on('response', (response) => {
    if (response.status() >= 400) {
      console.error(
        `notes_route_http_error=${label}:${response.status()}:${response.url()}`,
      );
    }
  });

  const url = `${baseUrl}${path}?notes_route_diagnostic=${Date.now()}`;
  const response = await page.goto(url, {
    waitUntil: 'domcontentloaded',
    timeout: 30000,
  });
  console.log(
    `notes_route_document=${label}:status=${response?.status() ?? 'none'}:content_type=${response?.headers()['content-type'] ?? 'missing'}:url=${page.url()}`,
  );

  let flutterAttached = false;
  try {
    await page.waitForSelector('flutter-view', { state: 'attached', timeout: 15000 });
    flutterAttached = true;
  } catch (_) {
    // Diagnostics below deliberately preserve the page rather than masking the failure.
  }
  console.log(`notes_route_flutter_view=${label}:${flutterAttached ? 'ATTACHED' : 'MISSING'}`);

  if (!flutterAttached) {
    const scripts = await page.locator('script[src]').evaluateAll((elements) =>
      elements.map((element) => element.getAttribute('src')),
    );
    const html = (await page.content()).replace(/\s+/g, ' ').slice(0, 1200);
    console.error(`notes_route_scripts=${label}:${JSON.stringify(scripts)}`);
    console.error(`notes_route_html=${label}:${JSON.stringify(html)}`);
  }
  await page.close();
  return flutterAttached;
}

const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({ serviceWorkers: 'block' });
  const tasksAttached = await inspectRoute(context, '/tasks');
  const notesAttached = await inspectRoute(context, '/more/notes');
  console.log(
    `notes_route_diagnostic=${JSON.stringify({ tasksAttached, notesAttached })}`,
  );
} finally {
  await browser.close();
}
