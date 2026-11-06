// @vitest-environment jsdom
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PillNav from '../PillNav';

let root, container;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const items = [{ href: '/discover', label: 'Discover' }, { href: '#access', label: 'Access' }];
const render = (props = {}) => act(() => root.render(<PillNav logo="/logo.svg" items={items} {...props} />));
const click = element => act(() => element.click());

beforeEach(() => {
  container = document.createElement('div');
  document.body.append(container);
  root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); });

describe('React Bits PillNav', () => {
  it('folds into a menu whose open state, labels and links stay consistent', () => {
    const onMenuToggle = vi.fn();
    render({ collapse: 'always', onMenuToggle, menuOpenLabel: 'Open nav', menuCloseLabel: 'Close nav' });
    const button = container.querySelector('button[aria-controls]');
    expect(button.getAttribute('aria-expanded')).toBe('false');
    expect(button.getAttribute('aria-label')).toBe('Open nav');
    expect(document.getElementById(button.getAttribute('aria-controls'))).toBe(null);

    click(button);
    expect(button.getAttribute('aria-expanded')).toBe('true');
    expect(button.getAttribute('aria-label')).toBe('Close nav');
    const panel = document.getElementById(button.getAttribute('aria-controls'));
    expect([...panel.querySelectorAll('a')].map(a => a.getAttribute('href'))).toEqual(['/discover', '#access']);

    click(panel.querySelector('a'));
    expect(button.getAttribute('aria-expanded')).toBe('false');
    expect(onMenuToggle.mock.calls.map(([open]) => open)).toEqual([true, false]);
  });

  it('closes on Escape, returns focus, and marks the current page in RTL', () => {
    container.dir = 'rtl';
    render({ collapse: 'always', activeHref: '/discover' });
    const button = container.querySelector('button[aria-controls]');
    click(button);
    const panel = document.getElementById(button.getAttribute('aria-controls'));
    expect(panel.querySelector('a[href="/discover"]').getAttribute('aria-current')).toBe('page');
    act(() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })));
    expect(button.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(button);
  });

  it('renders inline pills with a rolling label and no menubar role', () => {
    render({ collapse: 'never', activeHref: '#access', linkComponent: 'a' });
    const links = container.querySelectorAll('.pill-nav__item');
    expect(links).toHaveLength(2);
    expect(links[1].getAttribute('aria-current')).toBe('page');
    expect(links[0].hasAttribute('aria-current')).toBe(false);
    expect(links[0].querySelector('.pill-nav__face-alt').getAttribute('aria-hidden')).toBe('true');
    expect(container.querySelector('[role="menubar"]')).toBe(null);
    expect(container.querySelector('nav').getAttribute('aria-label')).toBe('Main');
  });
});
