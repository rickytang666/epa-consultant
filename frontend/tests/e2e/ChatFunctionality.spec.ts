import { test, expect } from '@playwright/test';

test.describe('Chat Functionality & Constraints', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
    });

    test('Input validation: Send button disabled when empty', async ({ page }) => {
        const sendButton = page.getByRole('button').filter({ has: page.locator('svg.lucide-send-horizontal') });
        const input = page.getByPlaceholder('Ask about EPA regulations...');

        // Initially disabled
        await expect(sendButton).toBeDisabled();

        // Type whitespace only
        await input.fill('   ');
        await expect(sendButton).toBeDisabled();

        // Type valid text
        await input.fill('Hello');
        await expect(sendButton).toBeEnabled();
    });

    test('Keyboard Shortcuts: Shift+Enter inserts newline, Enter sends', async ({ page }) => {
        const input = page.getByPlaceholder('Ask about EPA regulations...');

        // 1. Shift+Enter
        await input.fill('Line 1');
        await input.press('Shift+Enter');
        await input.type('Line 2');

        // Verify value has newline
        const value = await input.inputValue();
        expect(value).toContain('Line 1\nLine 2');

        // Verify message was NOT sent yet (Chat list is empty or doesn't contain this text)
        const chatList = page.getByTestId('chat-list');
        await expect(chatList.getByText('Line 1\nLine 2')).not.toBeVisible();

        // 2. Enter sends
        await input.press('Enter');

        // Verify input cleared and message sent
        await expect(input).toBeEmpty();
        await expect(page.getByText('Line 1')).toBeVisible(); // inner text might flatten or contain it
    });

    test('Markdown Rendering: Displays bold text correctly', async ({ page }) => {
        // Mock the backend to return Markdown
        await page.route('/api/query', async route => {
            const body = `content: This is **bold** text.\n\n`;
            await route.fulfill({
                status: 200,
                contentType: 'text/event-stream',
                body: body
            });
        });

        const input = page.getByPlaceholder('Ask about EPA regulations...');
        await input.fill('Test Markdown');
        await input.press('Enter');

        // Look for the strong tag presence using CSS selector inside the message bubble
        const chatList = page.getByTestId('chat-list');
        const boldElement = chatList.locator('strong', { hasText: 'bold' });

        await expect(boldElement).toBeVisible();
    });

    test('Error Handling: Displays error bubble on network failure', async ({ page }) => {
        // Mock a network failure
        await page.route('/api/query', async route => {
            await route.abort('failed');
        });

        const input = page.getByPlaceholder('Ask about EPA regulations...');
        await input.fill('Trigger Error');
        await input.press('Enter');

        // Expect error message in Assistant bubble
        // The useChat hook sets content: "**Error:** Failed to get response."
        const chatList = page.getByTestId('chat-list');
        const errorMsg = chatList.getByText('Failed to get response');

        await expect(errorMsg).toBeVisible();
        // It should probably be styled as an error or at least be visible.
    });
});
