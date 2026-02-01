import { test, expect } from '@playwright/test';

test.describe('PDF Viewer & Sources', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('http://localhost:5173');
    });

    test('User can toggle the context panel', async ({ page }) => {
        // Initially closed or open depending on default? AppLayout sets default false.
        // Check if right panel is hidden
        await expect(page.locator('text=Source Context')).not.toBeVisible();

        // Click "Check References" button in header
        await page.click('button:has-text("Check References")');

        // Should be visible now
        await expect(page.locator('text=Source Context')).toBeVisible();

        // Click again (Hide)
        await page.click('button:has-text("Hide References")');
        await expect(page.locator('text=Source Context')).not.toBeVisible();
    });

    test('Receiving sources displays relevant pages', async ({ page }) => {
        // Mock the API response to return sources
        await page.route('/api/query', async route => {
            const encoder = new TextEncoder();
            const stream = new ReadableStream({
                start(controller) {
                    // Send source event
                    const sources = [
                        {
                            chunk_id: '1',
                            text: 'test',
                            metadata: { page_number: 1, document_id: 'doc1', header_path_str: '' }
                        },
                        {
                            chunk_id: '2',
                            text: 'test2',
                            metadata: { page_number: 3, document_id: 'doc1', header_path_str: '' }
                        }
                    ];
                    controller.enqueue(encoder.encode(`sources: ${JSON.stringify(sources)}\n\n`));

                    // Send content
                    controller.enqueue(encoder.encode('content: Here is the answer.\n\n'));
                    controller.close();
                }
            });

            await route.fulfill({
                status: 200,
                contentType: 'text/event-stream',
                body: stream, // Playwright handles stream body? workaround usually needed or use buffer
            });
            // Note: Playwright route body with stream might be tricky. 
            // Simpler approach: return string with correct headers, but fetch needs to read it.
            // Actually standard 'body' string works for short responses, 
            // but for streaming validation we need to ensure the client parses it.
            // Let's try simple body with the SSE format.
        });

        // We override the route above, but for simple body:
        await page.route('/api/query', async route => {
            const sources = JSON.stringify([
                { chunk_id: '1', text: 'test', metadata: { page_number: 1, document_id: 'd1', header_path_str: '' } },
                { chunk_id: '2', text: 'test', metadata: { page_number: 5, document_id: 'd1', header_path_str: '' } }
            ]);

            const responseBody = `sources: ${sources}\n\ncontent: Answer.\n\n`;

            await route.fulfill({
                status: 200,
                contentType: 'text/html', // Use text/html or text/plain if event-stream causes browser issues in mock, but fetch needs stream.
                // Actually, let's keep text/event-stream but provide full body.
                headers: { 'Content-Type': 'text/event-stream' },
                body: responseBody
            });
        });

        // Send a message
        await page.fill('textarea[placeholder="Type a message..."]', 'Test query');
        await page.keyboard.press('Enter');

        // Wait for the response to be processed
        await expect(page.locator('text=Answer.')).toBeVisible();

        // Open context panel (if not auto open)
        await page.click('button:has-text("Check References")');

        // Verify PDF Viewer is rendering Page 1 and Page 5
        // Note: PDF rendering might take time or fail if file not found. 
        // We hardcoded "/sample.pdf". Ideally we check if the container for page 1 exists.
        // Our Component renders: "Page 1 (Relevant)" badge.

        // We expect the badge to be present
        await expect(page.locator('text=Page 1 (Relevant)')).toBeVisible({ timeout: 10000 });
        await expect(page.locator('text=Page 5 (Relevant)')).toBeVisible();

        // Ensure Page 2 is NOT visible (filtered view)
        await expect(page.locator('text=Page 2 (Relevant)')).not.toBeVisible();
    });
    test('Zoom slider adjusts PDF page width', async ({ page }) => {
        // Mock sources to trigger PDF load
        await page.route('/api/query', async route => {
            const sources = JSON.stringify([
                { chunk_id: '1', text: 'zoom test', metadata: { page_number: 1, document_id: 'd1', header_path_str: '' } }
            ]);
            const responseBody = `sources: ${sources}\n\ncontent: Answer.\n\n`;
            await route.fulfill({
                status: 200,
                headers: { 'Content-Type': 'text/event-stream' },
                body: responseBody
            });
        });

        await page.goto('http://localhost:5173');
        await page.fill('textarea', 'test zoom');
        await page.keyboard.press('Enter');

        // Wait for PDF to render
        await expect(page.locator('text=Source Context')).toBeVisible();
        await page.waitForSelector('.react-pdf__Page');

        // Get initial width of the first page content
        const firstPage = page.locator('.react-pdf__Page').first();
        const initialBox = await firstPage.boundingBox();
        const initialWidth = initialBox?.width || 0;

        // Expect roughly 700px (allow small variance for borders/rendering)
        expect(initialWidth).toBeGreaterThan(690);
        expect(initialWidth).toBeLessThan(710);

        // Interact with Slider
        // ShadCN/Radix slider is tricky to automate with simple 'fill'. 
        // We simulate arrow keys on the slider thumb.
        const sliderThumb = page.locator('[role="slider"]');
        await sliderThumb.focus();
        // Press Right Arrow multiple times to increase zoom
        await page.keyboard.press('ArrowRight');
        await page.keyboard.press('ArrowRight');
        await page.keyboard.press('ArrowRight');
        await page.keyboard.press('ArrowRight');
        await page.keyboard.press('ArrowRight');

        // Allow render update
        await page.waitForTimeout(500);

        // Get new width
        const newBox = await firstPage.boundingBox();
        const newWidth = newBox?.width || 0;

        // Verify width increased
        expect(newWidth).toBeGreaterThan(initialWidth);
    });
});
