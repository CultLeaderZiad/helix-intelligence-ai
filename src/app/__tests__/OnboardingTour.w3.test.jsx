// @vitest-environment jsdom
import React, { act, StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { OnboardingTour } from '../OnboardingTour';

const { driver, drive, destroy, options } = vi.hoisted(() => ({
  driver: vi.fn(), drive: vi.fn(), destroy: vi.fn(), options: { current: null }
}));
vi.mock('driver.js', () => ({ driver }));
let root, container;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

beforeEach(() => {
  vi.useFakeTimers();
  vi.clearAllMocks();
  driver.mockImplementation(config => { options.current = config; return { drive, destroy }; });
  window.matchMedia = vi.fn(() => ({ matches: true }));
  container = document.createElement('div');
  document.body.append(container);
  root = createRoot(container);
});
afterEach(() => {
  act(() => root.unmount());
  container.remove();
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
    expect(drive).not.toHaveBeenCalled();
    await render({ user: { id: '1' }, onComplete });
    await act(async () => vi.advanceTimersByTime(400));
    expect(drive).toHaveBeenCalledTimes(1);
    await act(async () => { options.current.onDestroyStarted(); options.current.onDestroyStarted(); });
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(oldComplete).not.toHaveBeenCalled();
  });

  it('cancels the delayed drive on cleanup without completing onboarding', async () => {
    const onComplete = vi.fn();
    await render({ user: { id: '1' }, onComplete });
    await render({ user: null, onComplete });
    await act(async () => vi.advanceTimersByTime(1000));
    expect(drive).not.toHaveBeenCalled();
    expect(destroy).toHaveBeenCalledTimes(1);
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('does not start a stale import after unmount (including StrictMode replay)', async () => {
    await act(async () => {
      root.render(<StrictMode><OnboardingTour user={{ id: '1' }} /></StrictMode>);
      root.render(null);
    });
    await act(async () => { await vi.dynamicImportSettled(); vi.advanceTimersByTime(1000); });
    expect(drive).not.toHaveBeenCalled();
  });
});
