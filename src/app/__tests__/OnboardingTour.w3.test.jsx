// @vitest-environment jsdom
import React, { act, StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { OnboardingTour } from '../OnboardingTour';
import { ONBOARDING_TOUR_RESTART_EVENT } from '../../i18n/w5Onboarding';

const { driver, drive, destroy, options } = vi.hoisted(() => ({
  driver: vi.fn(), drive: vi.fn(), destroy: vi.fn(), options: { current: null }
}));
vi.mock('driver.js', () => ({ driver }));
let root, container;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

beforeEach(() => {
  vi.useFakeTimers();
  vi.clearAllMocks();
  driver.mockImplementation(config => {
    options.current = config;
    document.body.style.overflow = 'hidden';
    return { drive, destroy };
  });
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    value: vi.fn(() => ({ matches: true })),
  });
  container = document.createElement('div');
  document.body.append(container);
  for (const id of ['tour-discover-nav', 'tour-search-input', 'tour-results-area']) {
    const target = document.createElement('div');
    target.id = id;
    target.getBoundingClientRect = () => new DOMRect(0, 0, 100, 30);
    document.body.append(target);
  }
  root = createRoot(container);
});
afterEach(() => {
  act(() => root.unmount());
  container.remove();
  document.querySelectorAll('#tour-discover-nav, #tour-search-input, #tour-results-area').forEach(node => node.remove());
  document.body.style.overflow = '';
  window.history.replaceState({}, '', '/');
  vi.useRealTimers();
});
const render = async props => {
  await act(async () => { root.render(<OnboardingTour {...props} />); });
  await act(async () => { await vi.dynamicImportSettled(); });
};

describe('optional onboarding', () => {
  it('does not create a tour for signed-out, disabled, or completed users', async () => {
    await render({ user: null });
    await render({ user: { id: '1' }, enabled: false });
    await render({ user: { id: '1', has_completed_onboarding: true } });
    expect(driver).not.toHaveBeenCalled();
  });

  it('loads for an eligible user, honors reduced motion, and calls the latest completion once', async () => {
    const oldComplete = vi.fn(), onComplete = vi.fn();
    await render({ user: { id: '1' }, onComplete: oldComplete });
    expect(driver).toHaveBeenCalledTimes(1);
    expect(options.current.animate).toBe(false);
    expect(options.current.steps).toHaveLength(3);
    expect(drive).not.toHaveBeenCalled();
    await render({ user: { id: '1' }, onComplete });
    await act(async () => vi.advanceTimersByTime(400));
    expect(drive).toHaveBeenCalledTimes(1);
    await act(async () => { options.current.onDestroyStarted(); options.current.onDestroyStarted(); });
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(oldComplete).not.toHaveBeenCalled();
  });

  it('cancels the delayed drive on cleanup without completing onboarding', async () => {
    document.body.style.overflow = 'auto';
    const onComplete = vi.fn();
    await render({ user: { id: '1' }, onComplete });
    await render({ user: null, onComplete });
    await act(async () => vi.advanceTimersByTime(1000));
    expect(drive).not.toHaveBeenCalled();
    expect(destroy).toHaveBeenCalledTimes(1);
    expect(onComplete).not.toHaveBeenCalled();
    expect(document.body.style.overflow).toBe('auto');
  });

  it('does not start a stale import after unmount (including StrictMode replay)', async () => {
    await act(async () => {
      root.render(<StrictMode><OnboardingTour user={{ id: '1' }} /></StrictMode>);
      root.render(null);
    });
    await act(async () => { await vi.dynamicImportSettled(); vi.advanceTimersByTime(1000); });
    expect(drive).not.toHaveBeenCalled();
  });

  it('filters absent and hidden targets before configuring the tour', async () => {
    const search = document.querySelector('#tour-search-input');
    if (search instanceof HTMLElement) search.hidden = true;
    document.querySelector('#tour-results-area').remove();
    await render({ user: { id: '1' } });
    expect(options.current.steps.map(step => step.element)).toEqual(['#tour-discover-nav']);
  });

  it('allows a persisted restart event to replay a completed user tour', async () => {
    await render({ user: { id: '1', has_completed_onboarding: true }, enabled: false });
    expect(driver).not.toHaveBeenCalled();
    await act(async () => {
      window.dispatchEvent(new CustomEvent(ONBOARDING_TOUR_RESTART_EVENT, { detail: { persisted: true } }));
    });
    await act(async () => { await vi.dynamicImportSettled(); });
    expect(driver).toHaveBeenCalledTimes(1);
    await act(async () => vi.advanceTimersByTime(250));
    expect(drive).toHaveBeenCalledTimes(1);
    await act(async () => options.current.onDestroyStarted());
    expect(document.body.style.overflow).toBe('');
  });

  it('restarts from a settings route query and removes the one-shot query parameter', async () => {
    window.history.replaceState({}, '', '/discover?tour=restart');
    await render({ user: { id: '1', has_completed_onboarding: true }, enabled: false });
    expect(driver).toHaveBeenCalledTimes(1);
    expect(new URLSearchParams(window.location.search).has('tour')).toBe(false);
  });
});
