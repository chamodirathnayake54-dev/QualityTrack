import { expect, test, type Page } from '@playwright/test';
import type { Action, Cause, DefectEvent } from '../src/api/workflow';
import type { Defect } from '../src/api/defects';

async function checkScreen(page: Page, heading: string) {
  await expect(page.getByRole('heading', { name: heading, exact: true })).toBeFocused();
  await expect.poll(() => page.evaluate(() =>
    document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
}

test('login → photo-free capture → cause → investigation → Open action', async ({ page }) => {
  const lookup = { id: 'lookup-1', code: 'SAMPLE', label: 'Sample configured choice' };
  const snapshot = { id: lookup.id, code_at_capture: lookup.code, label_at_capture: lookup.label };
  const defect: Defect = {
    id: 'defect-1', part_number: 'SAMPLE-P100', defect_type: snapshot,
    production_line: snapshot, shift: snapshot, quantity_affected: 3, severity: 'Major',
    status: 'Open', created_by_ref: 'engineer', created_at: '2026-10-22T08:00:00Z',
    has_photo: false, revision: 1,
  };
  const causes: Cause[] = [];
  const actions: Action[] = [];
  const history: DefectEvent[] = [];
  const writes: string[] = [];
  const unexpected: string[] = [];
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1', '');
    const method = request.method();
    const reply = (json: unknown, status = 200) => route.fulfill({
      status, json, headers: { ETag: `"${defect.revision}"`, 'Cache-Control': 'private, no-store' },
    });
    const collection = (items: unknown[]) => reply({ items, next_cursor: null });
    if (path === '/auth/login' && method === 'POST') {
      expect(request.postDataJSON()).toEqual({ username: 'engineer', password: 'fixture-password' });
      return reply({ access_token: 'mock-token', token_type: 'bearer', expires_in: 3600 });
    }
    expect(request.headers().authorization).toBe('Bearer mock-token');
    if (path === '/me') return reply({
      ref: 'engineer', display_name: 'Quality Engineer', scope: 'plant', plant_zone: 'Etc/UTC',
      permissions: ['defect.capture', 'defect.read', 'cause.create', 'defect.investigate', 'action.assign'],
    });
    if (['/production-lines', '/shifts', '/defect-types'].includes(path)) return collection([lookup]);
    if (path === '/defects' && method === 'GET') return collection(writes.length ? [defect] : []);
    if (path === '/defects' && method === 'POST') {
      const body = request.postData() ?? '';
      expect(request.headers()['content-type']).toContain('multipart/form-data; boundary=');
      expect(body.match(/name="/g)).toHaveLength(1);
      expect(body).toContain('name="capture"');
      expect(body).not.toContain('name="photo"');
      expect(body).toContain('"severity":"Major"');
      expect(body).toContain('"quantity_affected":3');
      expect(request.headers()['if-match']).toBeUndefined();
      writes.push('capture');
      return reply(defect, 201);
    }
    if (path === '/defects/defect-1') return reply(defect);
    if (path === '/assignable-users') return collection([{ ref: 'owner-1', display_name: 'Assignable owner' }]);
    if (method === 'GET' && path.endsWith('/causes')) return collection(causes);
    if (method === 'GET' && path.endsWith('/actions')) return collection(actions);
    if (method === 'GET' && path.endsWith('/history')) return collection(history);
    if (method === 'POST' && path.endsWith('/causes')) {
      expect(request.postDataJSON()).toEqual({ text: 'Fixture clamp was loose' });
      expect(request.headers()['if-match']).toBeUndefined();
      defect.revision++;
      causes.push({ id: 'cause-1', defect_id: defect.id, text: 'Fixture clamp was loose',
        recorded_by_ref: 'engineer', recorded_at: defect.created_at, revision: defect.revision });
      writes.push('cause');
      return reply(causes[0], 201);
    }
    if (method === 'POST' && path.endsWith('/transitions')) {
      expect(causes).toHaveLength(1);
      expect(request.headers()['if-match']).toBe('"2"');
      expect(request.postDataJSON()).toEqual({ target_status: 'Under Investigation' });
      defect.status = 'Under Investigation';
      defect.revision++;
      history.push({ id: 'event-1', old_status: 'Open', new_status: defect.status,
        actor_ref: 'engineer', occurred_at: defect.created_at, aggregate_revision: defect.revision });
      writes.push('investigation');
      return reply(defect);
    }
    if (method === 'POST' && path.endsWith('/actions')) {
      expect(request.postDataJSON()).toEqual({
        description: 'Inspect fixture clamp', owner_ref: 'owner-1', due_date: '2026-11-01', status: 'Open',
      });
      expect(request.headers()['if-match']).toBeUndefined();
      defect.revision++;
      actions.push({ id: 'action-1', defect_id: defect.id, ...request.postDataJSON(), revision: defect.revision });
      writes.push('action');
      return reply(actions[0], 201);
    }
    unexpected.push(`${method} ${path}`);
    return route.fulfill({ status: 500, json: { status: 500, code: 'unexpected_mock', title: 'Unexpected request' } });
  });

  await page.goto('/login');
  await checkScreen(page, 'Sign in to QualityTrack');
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Username', { exact: true })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Password', { exact: true })).toBeFocused();
  await page.getByLabel('Username', { exact: true }).fill('engineer');
  await page.getByLabel('Password', { exact: true }).fill('fixture-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await checkScreen(page, 'Defects');
  await page.getByRole('link', { name: 'Log defect', exact: true }).first().click();
  await checkScreen(page, 'Log defect');
  await expect(page.locator('input[type=file]')).toHaveCount(0);
  await expect(page.getByText('Photo upload is not available in this version')).toBeVisible();
  await page.getByLabel('Part number *', { exact: true }).fill(defect.part_number);
  await page.getByLabel('Quantity affected *', { exact: true }).fill('3');
  for (const label of ['Production line *', 'Shift *', 'Defect type *']) {
    await page.getByLabel(label, { exact: true }).selectOption(lookup.id);
  }
  await page.getByRole('radio', { name: 'Major', exact: true }).check();
  await page.getByRole('button', { name: 'Log defect', exact: true }).click();
  await expect(page.getByText(/Defect logged/)).toBeVisible();
  await page.getByRole('link', { name: 'Continue to record cause' }).click();
  await checkScreen(page, 'Record cause');
  await page.getByLabel('Why did this defect occur?', { exact: true }).fill('Fixture clamp was loose');
  await page.getByRole('button', { name: 'Record cause', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Recorded causes' })).toContainText('Fixture clamp was loose');
  await page.getByRole('link', { name: 'Investigation', exact: true }).first().click();
  await checkScreen(page, 'Investigation');
  await expect(page.getByRole('region', { name: 'Recorded causes' })).toContainText('Fixture clamp was loose');
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Move to Under Investigation', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Status history' })).toContainText('Open → Under Investigation');
  await expect(page.getByRole('checkbox')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Move to Under Investigation', exact: true })).toBeDisabled();
  await page.getByRole('link', { name: 'Add corrective action', exact: true }).first().click();
  await checkScreen(page, 'Add corrective action');
  await page.getByLabel('Description *', { exact: true }).fill('Inspect fixture clamp');
  await page.getByLabel('Owner *', { exact: true }).selectOption('owner-1');
  await page.getByLabel('Due date *', { exact: true }).fill('2026-11-01');
  await page.getByLabel('Status *', { exact: true }).selectOption('Open');
  await page.getByRole('button', { name: 'Add action', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Associated actions' })).toContainText('Inspect fixture clamp · 2026-11-01 · Open');
  // Long server content must remain readable without expanding the page at either breakpoint.
  await page.getByLabel('Description *', { exact: true }).fill('LongContent'.repeat(150));
  await expect.poll(() => page.evaluate(() =>
    document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(writes).toEqual(['capture', 'cause', 'investigation', 'action']);
  expect(unexpected).toEqual([]);
});
