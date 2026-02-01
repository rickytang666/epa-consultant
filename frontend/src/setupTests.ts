import { vi } from 'vitest';
import '@testing-library/jest-dom'

// Mock scrollIntoView (not implemented in JSDOM)
window.HTMLElement.prototype.scrollIntoView = vi.fn();

