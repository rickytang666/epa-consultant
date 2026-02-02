import { test, expect } from '@playwright/test';

test.describe('Chat Interface', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
    });

    test('User can send a message', async ({ page }) => {
        // PRE-EMPTIVE: These selectors expect the following implementation:
        // - Textarea or input with placeholder "Type your message..." or aria-label/role
        // - A send button (often handling "Enter" key too)

        // 1. Locate Input
        // Ideally use getByPlaceholder or getByRole('textbox')
        const input = page.getByPlaceholder('Ask about EPA regulations...');
        await expect(input).toBeVisible();

        // 2. Type message
        const testMessage = "Test message " + Date.now();
        await input.fill(testMessage);

        // 3. Send
        // Assuming hitting Enter works, or clicking a send button
        // Let's test hitting key Enter first as it's critical for chat UX
        await input.press('Enter');

        // 4. Verify Message Appears in Chat List
        // The chat list should contain the message text
        const chatList = page.getByTestId('chat-list');
        const userBubble = chatList.locator('.bg-primary').filter({ hasText: testMessage });

        await expect(userBubble).toBeVisible();

        // 5. Verify Input is cleared
        await expect(input).toBeEmpty();
    });

    test('Chat stays stable (anti-jitter) when user scrolls up', async ({ page }) => {
        // This test simulates the "Scroll Jitter" risk.
        // It helps verify that incoming tokens don't force-scroll the user to bottom 
        // if they have manually scrolled up.

        // 1. Send a proper prompt to trigger a long response (mocked or real)
        const input = page.getByPlaceholder('Ask about EPA regulations...');
        await input.fill("Tell me a very long story about lead pipes.");
        await input.press('Enter');

        // 2. Wait for response to start streaming (Assistant bubble appears)
        const chatList = page.getByTestId('chat-list');
        // Wait for assistant bubble (bg-muted/80 is the new style)
        // We look for any element with assistant styling
        const assistantBubble = chatList.locator('.bg-muted\\/80');
        await expect(assistantBubble).toBeVisible({ timeout: 10000 });

        // 3. Scroll up manually
        // Simulate user scrolling up by 100px
        await chatList.evaluate(node => node.scrollTop -= 100);

        // Get current scroll position
        const scrollTopBefore = await chatList.evaluate(node => node.scrollTop);

        // 4. Wait a bit (simulating more tokens arriving)
        await page.waitForTimeout(2000);

        // 5. Verify scroll position HAS NOT changed (it pinned to user location)
        const scrollTopAfter = await chatList.evaluate(node => node.scrollTop);

        // Allow for tiny pixel differences due to rendering, but should be identical conceptually
        expect(Math.abs(scrollTopAfter - scrollTopBefore)).toBeLessThan(5);
    });


    test('Context Panel toggles correctly via Chat Action', async ({ page }) => {
        // This tests that clicking a "Check References" or citation button opens the panel.

        // 1. Identify the toggle button provided in the header or citations
        // 'Check References' button based on ChatLayout.tsx
        const refsButton = page.getByRole('button', { name: /Check References|Hide References/i });

        await expect(refsButton).toBeVisible();

        // 2. Click to toggle
        // Assumption: Starts closed or we check state. 
        // Based on AppLayout defaults, might be open or closed. Let's check text.
        const buttonText = await refsButton.textContent();

        if (buttonText?.includes('Check References')) {
            // It's closed, click to open
            await refsButton.click();
            await expect(page.getByRole('button', { name: 'Hide References' })).toBeVisible();
            // Verify Panel is visible (maybe check for a known element inside context panel)
            await expect(page.getByText('Source Context')).toBeVisible(); // Placeholder title or similar
        } else {
            // It's open, click to close
            await refsButton.click();
            await expect(page.getByRole('button', { name: 'Check References' })).toBeVisible();
        }
    });
});
