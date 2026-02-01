import { test, expect } from '@playwright/test';

test.describe('Advanced Citation & PDF Features', () => {
    test('Verifies Citations, Navigation, Tables, and Formatting', async ({ page }) => {
        // Mock API response with complex sources and content
        await page.route('/api/query', async route => {
            const sources = [
                // Source 1: Standard Page (Page 2)
                {
                    chunk_id: '1',
                    text: 'Regulation 123 Content',
                    metadata: {
                        page_number: 2,
                        document_id: 'doc1',
                        header_path_str: 'Regulations > Section 1'
                    }
                },
                // Source 2: Unmapped Source (No Page)
                {
                    chunk_id: '2',
                    text: 'Text Only Source Content',
                    metadata: {
                        page_number: null, // Simulate missing page
                        document_id: 'doc1',
                        header_path_str: 'Appendix A'
                    }
                },
                // Source 3: Complex Header (Arrow Separator)
                {
                    chunk_id: '3',
                    text: 'Deeply Nested Content',
                    metadata: {
                        page_number: 5,
                        document_id: 'doc1',
                        header_path_str: 'Part 9 → Section 9.1 → 9.1.1'
                    }
                }
            ];

            const textContent = `
Here is a response with multiple features:

1. **Standard Citation**: [Source: Regulations > Section 1]
2. **Bracket Styles**: 【Source: Appendix A】 and (Source: 9.1.1)
3. **Table Rendering**:

| Col A | Col B |
|-------|-------|
| Val 1 | Val 2 |

4. **Line Breaks**:
Line 1
Line 2 (Should be on new line)
            `;

            const responseBody = `sources: ${JSON.stringify(sources)}\n\ncontent: ${JSON.stringify(textContent)}\n\n`;

            await route.fulfill({
                status: 200,
                headers: { 'Content-Type': 'text/event-stream' },
                body: responseBody
            });
        });

        await page.goto('/');

        // Send a message
        await page.getByPlaceholder('Ask about EPA regulations...').fill('Test all features');
        await page.keyboard.press('Enter');

        // --- VERIFICATION START ---

        // 1. Verify Line Breaks (Paragraphs/Breaks)
        // remark-breaks renders newlines as <br>, so they might be in the same <p>.
        // We just check that the text is visible.
        await expect(page.locator('text=Line 2 (Should be on new line)')).toBeVisible();

        // 2. Verify Table Rendering
        const table = page.locator('table');
        await expect(table).toBeVisible();
        await expect(table.locator('th', { hasText: 'Col A' })).toBeVisible();
        await expect(table.locator('td', { hasText: 'Val 1' })).toBeVisible();

        // 3. Verify Citation Parsing (Mixed Styles)
        // Check for badges
        await expect(page.locator('.inline-flex', { hasText: 'Section 1' })).toBeVisible();
        await expect(page.locator('.inline-flex', { hasText: 'Appendix A' })).toBeVisible();
        await expect(page.locator('.inline-flex', { hasText: '9.1.1' })).toBeVisible();

        // 4. Verify Context Panel Exists
        await expect(page.locator('text=Source Context')).toBeVisible();

        // 5. Test Advanced Navigation (Arrow Separator & Fallback)
        // Click the "9.1.1" badge (matches Source 3 which has "Part 9 → ...")
        const deepBadge = page.locator('.inline-flex', { hasText: '9.1.1' });
        await deepBadge.click();

        // Should scroll to Page 5
        await expect(page.locator('text=Page 5 (Relevant)')).toBeVisible();

        // 6. Test Unmapped Source Navigation
        // Click "Appendix A" badge (Source 2, No Page)
        const unmappedBadge = page.locator('.inline-flex', { hasText: 'Appendix A' });
        await unmappedBadge.click();

        // Should verify we are seeing the "Other Sources" section
        await expect(page.locator('text=Other Sources (Text Only)')).toBeVisible();
        // Ideally we'd check scroll position, but visibility is a good proxy.
    });
});
