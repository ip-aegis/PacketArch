/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * useIdleLogout — log the user out after a period of no user activity.
 *
 * Why it exists: the session-timeout audit (see tasks/todo.md, T0.4) found
 * that leaving a PacketArch tab open overnight let the user walk straight
 * back in the next morning. Server-side we now cap the absolute session
 * length, but the user-visible expectation is that an idle browser logs
 * out on its own — that's this hook.
 *
 * Activity is sampled from `mousemove`, `mousedown`, `keydown`, `scroll`,
 * `touchstart`, and a `visibilitychange` that fires when the tab returns
 * to foreground. Each event resets a single setTimeout. We deliberately
 * do NOT use any keepalive ping — if you're actually using the app, the
 * UI emits events; if you aren't, you idle out.
 */

import { useEffect, useRef } from 'react';

const DEFAULT_IDLE_MS = 30 * 60 * 1000; // 30 minutes

interface UseIdleLogoutOptions {
  /**
   * Idle duration in milliseconds before triggering logout. Defaults to
   * 30 minutes — tuned for an OT/security app where leaving an authed
   * tab open is a meaningful risk.
   */
  idleMs?: number;
  /**
   * Whether the watcher should be armed. Pass `false` when the user is
   * logged out so the hook is a no-op on /login.
   */
  enabled?: boolean;
  /**
   * Called when the idle window elapses. Receives no arguments.
   */
  onIdle: () => void;
}

const ACTIVITY_EVENTS: Array<keyof WindowEventMap> = [
  'mousemove',
  'mousedown',
  'keydown',
  'scroll',
  'touchstart',
];

export function useIdleLogout({
  idleMs = DEFAULT_IDLE_MS,
  enabled = true,
  onIdle,
}: UseIdleLogoutOptions): void {
  // Stash the callback in a ref so changing it doesn't tear down the
  // listeners (which would also reset the timer at an unpredictable moment).
  const onIdleRef = useRef(onIdle);
  onIdleRef.current = onIdle;

  useEffect(() => {
    if (!enabled) return;

    let timerId: ReturnType<typeof setTimeout> | null = null;

    const fire = () => {
      onIdleRef.current();
    };

    const reset = () => {
      if (timerId !== null) clearTimeout(timerId);
      timerId = setTimeout(fire, idleMs);
    };

    const handleVisibility = () => {
      // When the tab comes back to foreground, restart the timer from
      // zero — the user is "actively here" again. (When it goes hidden,
      // we leave the timer running; idle is idle either way.)
      if (document.visibilityState === 'visible') {
        reset();
      }
    };

    // Arm initial timer + listeners.
    reset();
    for (const evt of ACTIVITY_EVENTS) {
      window.addEventListener(evt, reset, { passive: true });
    }
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      if (timerId !== null) clearTimeout(timerId);
      for (const evt of ACTIVITY_EVENTS) {
        window.removeEventListener(evt, reset);
      }
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [enabled, idleMs]);
}

export default useIdleLogout;
