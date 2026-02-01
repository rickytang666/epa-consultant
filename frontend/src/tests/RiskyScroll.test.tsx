import { describe, test, expect } from 'vitest';
import { render } from '@testing-library/react';
import { useEffect, useRef } from 'react';

// Mock scrollIntoView logic
// Since JSDOM has no real layout, we'll verify if 'scrollIntoView' is CALLED.

const RiskyChatList = ({ messages }: { messages: string[], userScrolledUp: boolean }) => {
    const endRef = useRef<HTMLDivElement>(null);

    // NAIVE IMPLEMENTATION: Always scroll
    // CORRECT IMPLEMENTATION: Check userScrolledUp flag
    useEffect(() => {
        // NAIVE LOGIC (Should fail requirement)
        // endRef.current?.scrollIntoView(); 

        // Let's implement the NAIVE logic first to prove fail
        if (messages.length > 0) {
            endRef.current?.scrollIntoView();
        }
    }, [messages]);

    return (
        <div>
            {messages.map((m, i) => <div key={i}>{m}</div>)}
            <div ref={endRef} />
        </div>
    );
};

describe('Risk: Scroll Jitter', () => {
    test('should NOT call scrollIntoView if userScrolledUp is true', () => {
        const { rerender } = render(<RiskyChatList messages={['1']} userScrolledUp={false} />);

        // Reset mock
        const scrollMock = window.HTMLElement.prototype.scrollIntoView as any;
        scrollMock.mockClear();

        // Act: New message comes in, but user IS scrolled up.
        rerender(<RiskyChatList messages={['1', '2']} userScrolledUp={true} />);

        // Assert
        // NAIVE implementation calls it anyway -> This should PASS the assertion "toHaveBeenCalled"
        // BUT we want to ASSERT that it was *NOT* called for a Correct implementation.
        // So for this test to "Fail" (proving the risk exists), we expect the naive code TO call it.

        // Wait, TDD means we write the test for the DESIRED behavior.
        // Desired: Should NOT call scrollIntoView.
        expect(window.HTMLElement.prototype.scrollIntoView).not.toHaveBeenCalled();
    });
});
