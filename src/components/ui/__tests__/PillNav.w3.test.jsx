// @vitest-environment jsdom
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PillNav from '../PillNav';

let root, container;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const items = [{ href: '/discover', label: 'Discover' }, { href: '#pricing', label: 'Pricing' }];
const render = (props = {}) => act(() => root.render(
  <MemoryRouter><PillNav logo="/logo.svg" items={items} {...props} /></MemoryRouter>
));
const click = element => act(() => element.click());

beforeEach(() => {
  container = document.createElement('div');
  document.body.append(container);
  root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); });

describe('native PillNav', () => {
  it('keeps mobile visibility and aria state consistent across rapid toggles and link clicks', () => {
    const onMobileMenuClick = vi.fn();
    render({ onMobileMenuClick });
    const button = container.querySelector('button');
    const menu = document.getElementById(button.getAttribute('aria-controls'));
    expect(menu.hidden).toBe(true);
    click(button);
    expect(button.getAttribute('aria-expanded')).toBe('true');
    expect(menu.hidden).toBe(false);
    click(button); click(button); click(button);
    expect(menu.hidden).toBe(true);
    click(button);
    click(menu.querySelector('a'));
    expect(menu.hidden).toBe(true);
    expect(button.getAttribute('aria-expanded')).toBe('false');
    expect(onMobileMenuClick).toHaveBeenCalledTimes(5);
  });

  it('supports Escape focus return, route changes, and current-page semantics in RTL', () => {
    container.dir = 'rtl';
    render({ activeHref: '/discover' });
    const button = container.querySelector('button');
    expect(container.querySelector('.pill').getAttribute('aria-current')).toBe('page');
    click(button);
    act(() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })));
    expect(button.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(button);
    click(button);
    render({ activeHref: '/other' });
    expect(button.getAttribute('aria-expanded')).toBe('false');
    expect(container.querySelector('.pill').hasAttribute('aria-current')).toBe(false);
    // Ordinary navigation links remain in the native Tab order (not an incomplete menubar).
    expect(container.querySelector('[role="menubar"]')).toBe(null);
  });
});
