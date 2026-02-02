import { test, expect } from '@playwright/test';

test.describe('App Layout & Sidebar', () => {
    test.beforeEach(async ({ page }) => {
        // Navigate to the app root
        await page.goto('/');
    });

    test('Sidebar should toggle open and close', async ({ page }) => {
        const sidebar = page.getByTestId('sidebar');

        // Initially sidebar should be expanded (default)
        await expect(sidebar).toBeVisible();
        await expect(page.getByTitle('Collapse Sidebar')).toBeVisible();

        // Click collapse
        await page.getByTitle('Collapse Sidebar').click();

        // Wait for animation if needed, check if expand button becomes visible
        await expect(page.getByTitle('Expand Sidebar')).toBeVisible();

        // Verify specific class or state indicating collapsed if possible, 
        // or just that the text 'EPA Consultant' is hidden/gone
        // Scope to sidebar to avoid finding "EPA Consultant" in the chat area
        // Use .first() if needed, but scoping should be enough if unique in sidebar
        await expect(sidebar.getByText('EPA Consultant')).not.toBeVisible();

        // Click expand
        await page.getByTitle('Expand Sidebar').click();

        // Verify expanded state
        await expect(page.getByTitle('Collapse Sidebar')).toBeVisible();
        await expect(sidebar.getByText('EPA Consultant')).toBeVisible();
    });

    test('Sidebar resize functionality', async ({ page }) => {
        // Locate the resize handle. 
        // react-resizable-panels handles usually have role="separator"
        const handle = page.getByRole('separator').first();

        await expect(handle).toBeVisible();

        // Get initial width of sidebar
        const sidebar = page.getByTestId('sidebar');
        const initialBox = await sidebar.boundingBox();
        if (!initialBox) throw new Error('Sidebar not found');

        // Drag the handle to the LEFT (shrink)
        await handle.hover();
        await page.mouse.down();
        // Move left significantly to ensure resize exceeds threshold
        await page.mouse.move(initialBox.x + initialBox.width - 50, initialBox.y + 100);
        await page.mouse.up();

        // Verify width changed
        const newBox = await sidebar.boundingBox();
        if (!newBox) throw new Error('Sidebar not found after resize');

        // Width should have decreased
        expect(newBox.width).toBeLessThan(initialBox.width);
    });

    test('Buttons should react to hover', async ({ page }) => {
        // Target the "New Chat" button sidebar
        const newChatBtn = page.getByRole('button', { name: 'New Chat' });

        await expect(newChatBtn).toBeVisible();

        // Get initial computed style
        // We check for background-color. Note that "outline" variant might have transparent bg initially.
        const initialBg = await newChatBtn.evaluate((el) => {
            return window.getComputedStyle(el).backgroundColor;
        });

        // Hover
        await newChatBtn.hover();

        // Wait for any transition/reactivity
        // We might need to wait for the style to change.
        // Use expect.poll or just a small wait if simple.
        // Better way: assert that the style eventually becomes different
        await expect(async () => {
            const hoverBg = await newChatBtn.evaluate((el) => {
                return window.getComputedStyle(el).backgroundColor;
            });
            expect(hoverBg).not.toBe(initialBg);
        }).toPass();
    });
});
