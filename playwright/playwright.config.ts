import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  reporter: [['line'], ['html', { outputFolder: '../artifacts/playwright-report', open: 'never' }]],
  use: {
    headless: true,
    viewport: { width: 1440, height: 900 },
  },
});
