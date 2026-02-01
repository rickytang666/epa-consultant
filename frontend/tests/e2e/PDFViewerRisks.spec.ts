import { test, expect } from '@playwright/test';

test.describe('PDF Viewer Risks & Highlighting', () => {
    test('Highlighting should handle fragmented text matches', async ({ page }) => {
        // Mock API
        await page.route('/api/query', async route => {
            const sources = JSON.stringify([
                { chunk_id: '1', text: 'U.S. Environmental Protection Agency', metadata: { page_number: 1, document_id: 'd1', header_path_str: '' } }
            ]);
            const responseBody = `sources: ${sources}\n\ncontent: Answer.\n\n`;

            await route.fulfill({
                status: 200,
                headers: { 'Content-Type': 'text/event-stream' },
                body: responseBody
            });
        });

        await page.goto('http://localhost:5173');
        await page.fill('textarea', 'test');
        await page.keyboard.press('Enter');

        // Wait for panel
        await expect(page.locator('text=Source Context')).toBeVisible();

        // We wait for the canvas or text layer
        await page.waitForSelector('.react-pdf__Page__textLayer');

        // Check for ANY mark tag
        const markCount = await page.locator('mark').count();

        // Strict assertion: We EXPECT highlighting to happen
        expect(markCount).toBeGreaterThan(0);
    });
});
