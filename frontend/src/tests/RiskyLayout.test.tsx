import { describe, test, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { useState } from 'react';

// --- MOCK COMPONENT ---
// Simulates a sidebar that can be collapsed
const RiskySidebar = () => {
    const [collapsed, setCollapsed] = useState(false);

    return (
        <div>
            <div data-testid="sidebar" style={{ width: collapsed ? 0 : 200, display: collapsed ? 'none' : 'block' }}>
                Sidebar Content
                <button onClick={() => setCollapsed(true)}>Collapse</button>
            </div>

            {/* 
         THE RISK: If this button is missing, user is stuck.
         We intentionally omit it in the "Naive" version to prove the test fails.
      */}
            {/* !collapsed && <button>Expand</button> */}
        </div>
    );
};

// --- THE TEST CASE ---

describe('Risk: Invisible Panel Trap', () => {
    test('should provide a way to restore sidebar when collapsed', () => {
        // 1. Arrange
        render(<RiskySidebar />);
        const sidebar = screen.getByTestId('sidebar');

        // 2. Act: User collapses the sidebar
        fireEvent.click(screen.getByText('Collapse'));

        // 3. Assert
        expect(sidebar).not.toBeVisible();

        // FAILURE CONDITION: There should be a visible trigger to re-open it.
        // This will fail because our naive component doesn't have one.
        const expandBtn = screen.getByRole('button', { name: /expand/i }); // Fuzzy match
        expect(expandBtn).toBeInTheDocument();
    });
});
