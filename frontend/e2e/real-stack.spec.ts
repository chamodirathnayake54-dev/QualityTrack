import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

type RecordData = Record<string, any>;
const passwords: Record<string, string> = JSON.parse(process.env.QA07_PASSWORDS ?? '{}');
const evidence: RecordData[] = [];
const events: RecordData[] = [];
let sequence = 0;

async function navigate(page: Page, path: string) {
  await page.evaluate(destination => {
    window.history.pushState({}, '', destination);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, path);
}

async function token(request: APIRequestContext, user = 'sample-engineer') {
  const response = await request.post('/api/v1/auth/login', {
    data: { username: user, password: passwords[user] },
  });
  expect(response.status()).toBe(200);
  return (await response.json()).access_token as string;
}

async function call(request: APIRequestContext, bearer: string, path: string,
  method = 'GET', body?: unknown, etag?: string) {
  const response = await request.fetch(`/api/v1${path}`, {
    method, headers: { Authorization: `Bearer ${bearer}`, ...(etag ? { 'If-Match': etag } : {}) },
    ...(body === undefined ? {} : { data: body }),
  });
  const data = response.headers()['content-type']?.includes('json') ? await response.json() : null;
  events.push({ method, path, status: response.status(), etag: response.headers().etag,
    code: data?.code });
  return { status: response.status(), data, etag: response.headers().etag, response };
}

async function login(page: Page, user = 'sample-engineer') {
  await page.goto('/login');
  await page.getByLabel('Username', { exact: true }).fill(user);
  await page.getByLabel('Password', { exact: true }).fill(passwords[user]);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();
}

async function payload(request: APIRequestContext, bearer: string) {
  const choices: RecordData = {};
  for (const [key, path] of [
    ['defect_type_id', '/defect-types'], ['production_line_id', '/production-lines'], ['shift_id', '/shifts'],
  ]) choices[key] = (await call(request, bearer, path)).data.items[0];
  return {
    choices,
    body: {
      part_number: `QA07-${Date.now()}-${++sequence}`, quantity_affected: 3, severity: 'Major',
      ...Object.fromEntries(Object.entries(choices).map(([key, value]) => [key, (value as RecordData).id])),
    },
  };
}

async function capture(request: APIRequestContext, bearer: string) {
  const { body, choices } = await payload(request, bearer);
  const response = await request.post('/api/v1/defects', {
    headers: { Authorization: `Bearer ${bearer}` }, multipart: { capture: JSON.stringify(body) },
  });
  expect(response.status()).toBe(201);
  const defect = await response.json();
  evidence.push({ fixture: defect.id, part_number: body.part_number });
  return { defect, body, choices };
}

async function openCapture(page: Page, body: RecordData) {
  await navigate(page, '/defects');
  await expect(page.getByRole('heading', { name: 'Defects', exact: true })).toBeVisible();
  await navigate(page, '/defects/new');
  await page.getByLabel('Part number *', { exact: true }).fill(body.part_number);
  await page.getByLabel('Quantity affected *', { exact: true }).fill(String(body.quantity_affected));
  for (const [label, key] of [
    ['Production line *', 'production_line_id'], ['Shift *', 'shift_id'], ['Defect type *', 'defect_type_id'],
  ]) await page.getByLabel(label, { exact: true }).selectOption(body[key]);
  if (body.severity) await page.getByRole('radio', { name: body.severity, exact: true }).check();
}

async function actionFields(page: Page, description: string, status = 'Open') {
  await page.getByLabel('Description *', { exact: true }).fill(description);
  await page.getByLabel('Owner *', { exact: true }).selectOption('sample-engineer');
  await page.getByLabel('Due date *', { exact: true }).fill('2026-11-01');
  await page.getByLabel('Status *', { exact: true }).selectOption(status);
}

test.afterEach(async ({}, info) => {
  evidence.push({ case: info.title, status: info.status, at: new Date().toISOString() });
  const path = join(process.env.QA07_EVIDENCE!, 'browser.json');
  const saved = JSON.parse(readFileSync(path, 'utf8'));
  writeFileSync(path, JSON.stringify({
    evidence: [...saved.evidence, ...evidence.splice(0)],
    http: [...saved.http, ...events.splice(0)],
  }, null, 2) + '\n');
});

test('01 missing configuration then valid login and lookups', async ({ page, request }) => {
  await page.goto('http://127.0.0.1:4174/login');
  await expect(page.getByRole('heading', { name: 'Configuration required' })).toBeVisible();
  await login(page);
  const bearer = await token(request);
  const { body } = await payload(request, bearer);
  await openCapture(page, body);
  await expect(page.getByLabel('Defect type *', { exact: true })).toHaveValue(body.defect_type_id);
});

for (const run of [1, 2]) {
  test(`02/03/07/09/11/12 critical journey run ${run}`, async ({ page, request }) => {
    await login(page);
    const bearer = await token(request);
    const { body, choices } = await payload(request, bearer);
    await openCapture(page, body);
    for (const [label, key] of [
      ['Production line *', 'production_line_id'], ['Shift *', 'shift_id'], ['Defect type *', 'defect_type_id'],
    ]) await expect(page.getByLabel(label, { exact: true }).locator('option:checked'))
      .toHaveText(`${choices[key].code} — ${choices[key].label}`);
    const created = page.waitForResponse(r => r.url().endsWith('/api/v1/defects') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Log defect', exact: true }).click();
    const response = await created;
    expect(response.status()).toBe(201);
    const defect = await response.json();
    evidence.push({ journey: run, defect_id: defect.id, capture: defect });
    const base = `/defects/${defect.id}`;
    const saved = (await call(request, bearer, base)).data;
    for (const [field, key] of [
      ['defect_type', 'defect_type_id'], ['production_line', 'production_line_id'], ['shift', 'shift_id'],
    ]) expect(saved[field]).toEqual({
      id: choices[key].id, code_at_capture: choices[key].code, label_at_capture: choices[key].label,
    });
    await page.getByRole('link', { name: 'Continue to record cause' }).click();
    for (const text of ['', '   ']) {
      await page.getByLabel('Why did this defect occur?', { exact: true }).fill(text);
      await page.getByRole('button', { name: 'Record cause', exact: true }).click();
      await expect(page.getByText('Record at least one nonblank cause before moving to Under Investigation').first()).toBeVisible();
    }
    expect((await call(request, bearer, `${base}/causes`)).data.items).toHaveLength(0);
    await page.getByLabel('Why did this defect occur?', { exact: true }).fill('  Fixture clamp loose  ');
    await page.getByRole('button', { name: 'Record cause', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Recorded causes' })).toContainText('Fixture clamp loose');
    await page.getByRole('link', { name: 'Review investigation step' }).click();
    await page.getByRole('checkbox').check();
    await page.getByRole('button', { name: 'Move to Under Investigation', exact: true }).click();
    await expect(page.getByRole('region', { name: 'Transition history' })).toContainText('Open → Under Investigation');
    await expect(page.getByRole('region', { name: 'Transition history' })).toContainText('sample-engineer');
    await expect(page.getByRole('region', { name: 'Transition history' })).toContainText('Etc/UTC');
    const history = (await call(request, bearer, `${base}/history`)).data.items;
    expect(history).toHaveLength(1);
    expect(history[0]).toMatchObject({ actor_ref: 'sample-engineer', old_status: 'Open', new_status: 'Under Investigation', aggregate_revision: 3 });
    expect(Number.isNaN(Date.parse(history[0].occurred_at))).toBe(false);
    await page.getByRole('link', { name: 'Add corrective action', exact: true }).click();
    for (const [index, status] of ['Open', 'In Progress'].entries()) {
      await actionFields(page, `QA07-work-${run}-${index}`, status);
      await page.getByRole('button', { name: 'Add action', exact: true }).click();
      await expect(page.getByRole('region', { name: 'Associated actions' })).toContainText(`QA07-work-${run}-${index}`);
    }
    const actions = (await call(request, bearer, `${base}/actions`)).data.items;
    expect(actions).toHaveLength(2);
    expect(actions.map((a: RecordData) => a.status).sort()).toEqual(['In Progress', 'Open']);
    expect(actions.every((a: RecordData) => a.defect_id === defect.id && a.owner_ref === 'sample-engineer' && a.due_date === '2026-11-01')).toBe(true);
    await page.reload();
    await expect(page.getByRole('heading', { name: 'Sign in to QualityTrack' })).toBeVisible();
    await login(page);
    await navigate(page, `${base}/actions`);
    for (const action of actions) await expect(page.getByRole('region', { name: 'Associated actions' })).toContainText(action.description);
    await navigate(page, `${base}/investigation`);
    await expect(page.getByRole('region', { name: 'Transition history' })).toContainText('Open → Under Investigation');
    expect((await call(request, bearer, `${base}/history`)).data.items).toEqual(history);
    expect((await call(request, bearer, `${base}/causes`)).data.items[0].text).toBe('Fixture clamp loose');
    evidence.push({ journey: run, history, actions, final: (await call(request, bearer, base)).data });
  });
}

test('04 each missing capture field, quantity variants and explicit severities', async ({ page, request }) => {
  await login(page);
  const bearer = await token(request);
  const { body } = await payload(request, bearer);
  for (const label of ['Part number *', 'Quantity affected *', 'Production line *', 'Shift *', 'Defect type *', 'Severity *']) {
    await openCapture(page, body);
    if (label === 'Severity *') {
      // Fresh form is required because radio groups cannot be unchecked by a user.
      await navigate(page, '/defects');
      await expect(page.getByRole('heading', { name: 'Defects', exact: true })).toBeVisible();
      await openCapture(page, { ...body, severity: '' });
    } else if (['Production line *', 'Shift *', 'Defect type *'].includes(label)) {
      await page.getByLabel(label, { exact: true }).selectOption('');
    } else await page.getByLabel(label, { exact: true }).fill('');
    await page.getByRole('button', { name: 'Log defect', exact: true }).click();
    await expect(page.getByRole('alert').first()).toBeVisible();
  }
  for (const quantity of ['0', '-1', '1.5']) {
    await openCapture(page, body);
    await page.getByLabel('Quantity affected *', { exact: true }).fill(quantity);
    await page.getByRole('button', { name: 'Log defect', exact: true }).click();
    await expect(page.getByLabel('Part number *', { exact: true })).toHaveValue(body.part_number);
    await expect(page.getByText('Enter a positive whole number from 1 to 1,000,000').first()).toBeVisible();
  }
  expect((await call(request, bearer, `/defects?part_number=${body.part_number}`)).data.items).toHaveLength(0);
  for (const severity of ['Critical', 'Major', 'Minor']) {
    await openCapture(page, { ...body, severity, quantity_affected: 1 });
    const response = page.waitForResponse(r => r.url().endsWith('/api/v1/defects') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Log defect', exact: true }).click();
    expect(await (await response).json()).toMatchObject({ severity, quantity_affected: 1 });
  }
});

test('05 capture denied at UI and API boundary', async ({ page, request }) => {
  const engineer = await token(request);
  const { body } = await payload(request, engineer);
  await login(page, 'qa-no-capture');
  await navigate(page, '/defects/new');
  await expect(page.getByText('You do not have permission for this request.').first()).toBeVisible();
  const denied = await token(request, 'qa-no-capture');
  const response = await request.post('/api/v1/defects', {
    headers: { Authorization: `Bearer ${denied}` }, multipart: { capture: JSON.stringify(body) },
  });
  expect(response.status()).toBe(403);
  expect((await call(request, engineer, `/defects?part_number=${body.part_number}`)).data.items).toHaveLength(0);
});

test('06 retire selected type through API and preserve prior snapshot', async ({ page, request }) => {
  const bearer = await token(request);
  const { defect, body } = await capture(request, bearer);
  await login(page);
  await openCapture(page, { ...body, part_number: 'QA07-retired-rejected' });
  const custodian = await token(request, 'sample-supervisor');
  expect((await call(request, custodian, `/defect-types/${body.defect_type_id}/retire`, 'POST', {}, '"1"')).status).toBe(200);
  const response = page.waitForResponse(r => r.url().endsWith('/api/v1/defects') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Log defect', exact: true }).click();
  expect((await response).status()).toBe(409);
  expect((await call(request, bearer, '/defects?part_number=QA07-retired-rejected')).data.items).toHaveLength(0);
  expect((await call(request, bearer, `/defects/${defect.id}`)).data.defect_type).toEqual(defect.defect_type);
  await navigate(page, '/defects');
  await expect(page.getByRole('heading', { name: 'Defects', exact: true })).toBeVisible();
  await navigate(page, '/defects/new');
  await expect(page.getByLabel('Defect type *', { exact: true }).locator(`option[value="${body.defect_type_id}"]`)).toHaveCount(0);
});

test('08 unsaved cause cannot satisfy investigation presence gate', async ({ page, request }) => {
  const bearer = await token(request);
  const { defect } = await capture(request, bearer);
  await login(page);
  await navigate(page, `/defects/${defect.id}/causes`);
  await page.getByLabel('Why did this defect occur?', { exact: true }).fill('Not saved');
  await page.getByRole('link', { name: 'Review investigation step' }).click();
  await page.getByRole('checkbox').check();
  const response = page.waitForResponse(r => r.url().endsWith('/transitions') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Move to Under Investigation', exact: true }).click();
  expect((await response).status()).toBe(409);
  expect((await call(request, bearer, `/defects/${defect.id}`)).data.status).toBe('Open');
  expect((await call(request, bearer, `/defects/${defect.id}/history`)).data.items).toHaveLength(0);
});

test('10 exact stale ETag, renewed review, and denied transition UI', async ({ page, request }) => {
  const bearer = await token(request);
  const { defect } = await capture(request, bearer);
  const base = `/defects/${defect.id}`;
  await call(request, bearer, `${base}/causes`, 'POST', { text: 'First cause' });
  await login(page);
  await navigate(page, `${base}/investigation`);
  await page.getByRole('checkbox').check();
  await call(request, bearer, `${base}/causes`, 'POST', { text: 'Concurrent cause' });
  const response = page.waitForResponse(r => r.url().endsWith('/transitions') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Move to Under Investigation', exact: true }).click();
  const stale = await response;
  expect(stale.status()).toBe(412);
  expect(stale.request().headers()['if-match']).toBe('"2"');
  await expect(page.getByText(/Refreshed context requires renewed review/)).toBeVisible();
  await expect(page.getByRole('checkbox')).not.toBeChecked();
  expect((await call(request, bearer, `${base}/history`)).data.items).toHaveLength(0);
  await page.getByRole('button', { name: 'Sign out' }).click();
  await login(page, 'qa-no-transition');
  await navigate(page, `${base}/investigation`);
  await page.getByRole('checkbox').check();
  const denial = page.waitForResponse(r => r.url().endsWith('/transitions') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Move to Under Investigation', exact: true }).click();
  expect((await denial).status()).toBe(403);
  expect((await call(request, bearer, `${base}/history`)).data.items).toHaveLength(0);
});

test('11 required action fields each reject without writes', async ({ page, request }) => {
  const bearer = await token(request);
  const { defect } = await capture(request, bearer);
  await login(page);
  await navigate(page, `/defects/${defect.id}/actions`);
  for (const label of ['Description *', 'Owner *', 'Due date *', 'Status *']) {
    await actionFields(page, 'QA07-incomplete');
    if (['Owner *', 'Status *'].includes(label)) await page.getByLabel(label, { exact: true }).selectOption('');
    else await page.getByLabel(label, { exact: true }).fill('');
    await page.getByRole('button', { name: 'Add action', exact: true }).click();
    await expect(page.getByRole('alert').first()).toBeVisible();
  }
  expect((await call(request, bearer, `/defects/${defect.id}/actions`)).data.items).toHaveLength(0);
});

test('13 delayed real read cannot cross logout into denied-reader session', async ({ page, request }) => {
  const bearer = await token(request);
  const { defect } = await capture(request, bearer);
  await login(page);
  let release!: () => void;
  let fetched!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  const ready = new Promise<void>(resolve => { fetched = resolve; });
  await page.route(`**/api/v1/defects/${defect.id}`, async route => {
    const real = await route.fetch();
    fetched();
    await held;
    await route.fulfill({ response: real }).catch(() => undefined);
  });
  await navigate(page, `/defects/${defect.id}/causes`);
  await ready;
  await page.getByRole('button', { name: 'Sign out' }).click();
  await login(page, 'qa-no-read');
  release();
  await page.unrouteAll({ behavior: 'wait' });
  await navigate(page, `/defects/${defect.id}/causes`);
  await expect(page.getByText('You do not have permission for this request.').first()).toBeVisible();
  await expect(page.getByText(defect.part_number, { exact: true })).toHaveCount(0);
  const denied = await token(request, 'qa-no-read');
  expect((await call(request, denied, `/defects/${defect.id}/causes`, 'POST', { text: 'Forbidden' })).status).toBe(403);
});

test('14 optional photo requirement remains unmet, API rejects safely', async ({ page, request }) => {
  const bearer = await token(request);
  const { body } = await payload(request, bearer);
  await login(page);
  await openCapture(page, body);
  await expect(page.locator('input[type=file]')).toHaveCount(0);
  await expect(page.getByText('Photo upload is not available in this version')).toBeVisible();
  const response = await request.post('/api/v1/defects', {
    headers: { Authorization: `Bearer ${bearer}` },
    multipart: { capture: JSON.stringify(body),
      photo: { name: 'synthetic.png', mimeType: 'image/png', buffer: Buffer.from('synthetic') } },
  });
  expect(response.status()).toBe(422);
  expect((await response.json()).code).toBe('photo_not_supported');
  expect((await call(request, bearer, `/defects?part_number=${body.part_number}`)).data.items).toHaveLength(0);
  evidence.push({ case: '14', acceptance: 'FAILED requirement gap; defensive rejection is not photo acceptance' });
});

test('15-19 supporting backend evidence only; missing browser journeys are not passes', async ({ request }) => {
  const engineer = await token(request);
  const supervisor = await token(request, 'sample-supervisor');
  const auditor = await token(request, 'sample-auditor');
  const denied = await token(request, 'qa-supervisor-denied');
  const { defect } = await capture(request, engineer);
  const base = `/defects/${defect.id}`;
  await call(request, engineer, `${base}/causes`, 'POST', { text: 'Supporting lifecycle' });
  expect((await call(request, engineer, `${base}/transitions`, 'POST', { target_status: 'Under Investigation' }, '"2"')).status).toBe(200);
  const action = await call(request, supervisor, `${base}/actions`, 'POST', {
    description: 'Past due work', owner_ref: 'sample-engineer', due_date: '2020-01-01', status: 'Open',
  });
  expect(action.status).toBe(201);
  expect((await call(request, supervisor, `${base}/transitions`, 'POST', { target_status: 'Closed' }, '"4"')).status).toBe(409);
  expect((await call(request, supervisor, `/actions/${action.data.id}/transitions`, 'POST', { target_status: 'Complete' }, '"4"')).status).toBe(422);
  expect((await call(request, supervisor, '/overdue-actions')).data.items.some((a: RecordData) => a.id === action.data.id || a.action_id === action.data.id)).toBe(true);
  expect((await call(request, supervisor, `/actions/${action.data.id}/transitions`, 'POST',
    { target_status: 'Complete', completion_notes: 'Synthetic completion evidence' }, '"4"')).status).toBe(200);
  expect((await call(request, supervisor, `${base}/transitions`, 'POST', { target_status: 'Closed' }, '"5"')).status).toBe(200);
  // Closed-parent action reopening is deliberately unavailable, not implicit reopening.
  expect((await call(request, supervisor, `/actions/${action.data.id}/transitions`, 'POST',
    { target_status: 'In Progress', reopen_reason: 'Synthetic repeat' }, '"6"')).status).toBe(503);
  expect((await call(request, supervisor, `${base}/transitions`, 'POST',
    { target_status: 'Under Investigation' }, '"6"')).status).toBe(200);
  expect((await call(request, supervisor, `/actions/${action.data.id}/transitions`, 'POST',
    { target_status: 'In Progress', reopen_reason: 'Recheck after explicit parent reopening' }, '"7"')).status).toBe(200);
  const cycles = (await call(request, supervisor, `/actions/${action.data.id}/history`)).data.items;
  expect(cycles.map((event: RecordData) => event.new_status)).toEqual(['Open', 'Complete', 'In Progress']);
  expect(cycles[1].completion_notes).toBe('Synthetic completion evidence');
  expect(cycles[2].reopen_reason).toBe('Recheck after explicit parent reopening');
  const calendar = await capture(request, engineer);
  const today = new Date();
  const dateAt = (offset: number) => new Date(Date.UTC(
    today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate() + offset,
  )).toISOString().slice(0, 10);
  const boundaryIds: string[] = [];
  for (const [offset, status] of [[-1, 'Open'], [0, 'Open'], [1, 'Open'], [-1, 'Complete']] as const) {
    const created = await call(request, supervisor, `/defects/${calendar.defect.id}/actions`, 'POST', {
      description: `Calendar ${offset} ${status}`, owner_ref: 'sample-engineer',
      due_date: dateAt(offset), status,
      ...(status === 'Complete' ? { completion_notes: 'Already complete' } : {}),
    });
    expect(created.status).toBe(201);
    boundaryIds.push(created.data.id);
  }
  const overdue = await call(request, supervisor, '/overdue-actions?limit=100');
  const overdueIds = overdue.data.items.map((item: RecordData) => item.id ?? item.action_id);
  expect(overdueIds).toContain(boundaryIds[0]);
  for (const id of boundaryIds.slice(1)) expect(overdueIds).not.toContain(id);
  expect(overdueIds).toContain(action.data.id);
  evidence.push({ supporting: '15 calendar boundaries API only', reference_date: dateAt(0),
    fixture_ids: boundaryIds, overdue: overdue.data, action_cycles: cycles });
  for (const target_status of ['Closed', 'Open']) {
    expect((await call(request, denied, `${base}/transitions`, 'POST', { target_status }, '"6"')).status).toBe(403);
  }
  expect((await call(request, denied, `${base}/audit.pdf`)).status).toBe(403);
  const pdf = await call(request, auditor, `${base}/audit.pdf`);
  expect(pdf.status).toBe(200);
  expect((await pdf.response.body()).subarray(0, 5).toString()).toBe('%PDF-');
  for (const [user, path] of [['qa-no-read', base], ['qa-no-read', `${base}/audit.pdf`], ['qa-no-export', `${base}/audit.pdf`]]) {
    expect((await call(request, await token(request, user), path)).status).toBe(403);
  }
  expect((await call(request, auditor, `${base}/causes`, 'POST', { text: 'Denied' })).status).toBe(403);
  expect((await call(request, auditor, `${base}/actions`, 'POST', {
    description: 'Denied', owner_ref: 'sample-engineer', due_date: '2026-11-01', status: 'Open',
  })).status).toBe(403);
  const captureDenied = await request.post('/api/v1/defects', {
    headers: { Authorization: `Bearer ${auditor}` }, multipart: { capture: '{}' },
  });
  expect(captureDenied.status()).toBe(403);
  evidence.push({ supporting: '15-19 API only', defect_id: defect.id,
    history: (await call(request, engineer, `${base}/history`)).data.items });
});

test('20 lose response after actual commit; one POST and UI reconciliation', async ({ page, request }) => {
  const bearer = await token(request);
  const { defect } = await capture(request, bearer);
  await login(page);
  await navigate(page, `/defects/${defect.id}/actions`);
  const description = `QA07-lost-${Date.now()}`;
  let writes = 0;
  await page.route(`**/api/v1/defects/${defect.id}/actions`, async route => {
    if (route.request().method() !== 'POST') return route.continue();
    writes++;
    const actual = await route.fetch();
    expect(actual.status()).toBe(201);
    events.push({ fault: 'drop real committed action response', status: actual.status(),
      action_id: (await actual.json()).id });
    await route.abort('failed');
  });
  await actionFields(page, description);
  await page.getByRole('button', { name: 'Add action', exact: true }).click();
  await expect(page.getByText('The result is unconfirmed. Check the refreshed record before deliberately submitting again.')).toBeVisible();
  await expect(page.getByRole('region', { name: 'Associated actions' })).toContainText(description);
  expect(writes).toBe(1);
  const actions = (await call(request, bearer, `/defects/${defect.id}/actions`)).data.items;
  expect(actions.filter((a: RecordData) => a.description === description)).toHaveLength(1);
  await expect(page.getByLabel('Description *', { exact: true })).toHaveValue(description);
  await page.unrouteAll({ behavior: 'wait' });
  evidence.push({ case: '20', defect_id: defect.id, writes, actions,
    ui: 'Unconfirmed warning; refreshed associated action visible; draft retained; no retry' });
});
