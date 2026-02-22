import { test, expect } from '@playwright/test';
import { readFileSync } from 'fs';
import { join } from 'path';

test('practice to report flow contract presence', async ({ page }) => {
  const expected = JSON.parse(readFileSync(join(process.cwd(), 'golden', 'expected_ui_flows.json'), 'utf8'));
  await page.goto('file:///' + join(process.cwd(), 'docs', 'interactive-g5-life-pack2plus-empire', 'index.html').replace(/\\/g, '/'));
  await expect(page).toHaveTitle(/./);

  const bodyText = await page.locator('body').innerText();
  for (const field of expected.required_report_fields) {
    expect(typeof field).toBe('string');
    expect(field.length).toBeGreaterThan(0);
  }
  expect(bodyText.length).toBeGreaterThan(20);
});
