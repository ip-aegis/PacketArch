/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Scenario Lifecycle Manager
 * Coordinates all store resets and async cancellation when switching scenarios
 */

import { useCallback, useRef, useEffect } from 'react';
import { useScenarioStore } from '../stores/scenarioStore';
import { useHistoryStore } from '../stores/historyStore';
import { useAIAssistantStore } from '../stores/aiAssistantStore';
import { useUIStore } from '../stores/uiStore';

interface LifecycleState {
  currentScenarioId: string | null;
  abortController: AbortController | null;
  saveTimeoutId: ReturnType<typeof setTimeout> | null;
}

export const useScenarioLifecycle = () => {
  const stateRef = useRef<LifecycleState>({
    currentScenarioId: null,
    abortController: null,
    saveTimeoutId: null,
  });

  /**
   * Reset all stores atomically when switching scenarios
   */
  const resetAllStores = useCallback(() => {
    // Reset scenario store
    useScenarioStore.getState().resetScenario();

    // Clear undo/redo history
    useHistoryStore.getState().clear();

    // Clear selection and property context
    useUIStore.getState().clearSelection();
    useUIStore.getState().setPropertyContext(null, []);

    // Close AI panel if open (this also clears its conversation)
    const aiStore = useAIAssistantStore.getState();
    if (aiStore.isOpen) {
      aiStore.closePanel();
    }
  }, []);

  /**
   * Cancel any pending async operations (API calls, auto-save, etc.)
   */
  const cancelPendingOperations = useCallback(() => {
    if (stateRef.current.abortController) {
      stateRef.current.abortController.abort();
      stateRef.current.abortController = null;
    }
    if (stateRef.current.saveTimeoutId) {
      clearTimeout(stateRef.current.saveTimeoutId);
      stateRef.current.saveTimeoutId = null;
    }
  }, []);

  /**
   * Switch to a new scenario, resetting all stores and cancelling pending operations
   * Returns an AbortSignal for the caller to use with async operations
   */
  const switchScenario = useCallback(
    (newId: string | null): AbortSignal | undefined => {
      const previousId = stateRef.current.currentScenarioId;

      // Same scenario - no reset needed
      if (previousId === newId) {
        return stateRef.current.abortController?.signal;
      }

      // 1. Cancel any pending operations for previous scenario
      cancelPendingOperations();

      // 2. Reset all stores atomically
      resetAllStores();

      // 3. Update tracking
      stateRef.current.currentScenarioId = newId;
      stateRef.current.abortController = new AbortController();

      // 4. Return the abort signal for the caller to use
      return stateRef.current.abortController.signal;
    },
    [cancelPendingOperations, resetAllStores]
  );

  /**
   * Check if the given scenario ID is still the current one
   * Useful for race condition protection after async operations
   */
  const isCurrentScenario = useCallback((scenarioId: string | null): boolean => {
    return stateRef.current.currentScenarioId === scenarioId;
  }, []);

  /**
   * Get the current abort signal (for late-binding to async operations)
   */
  const getAbortSignal = useCallback((): AbortSignal | undefined => {
    return stateRef.current.abortController?.signal;
  }, []);

  /**
   * Register a save timeout (for cleanup on scenario switch)
   */
  const setSaveTimeout = useCallback((timeoutId: ReturnType<typeof setTimeout>) => {
    // Clear any existing timeout
    if (stateRef.current.saveTimeoutId) {
      clearTimeout(stateRef.current.saveTimeoutId);
    }
    stateRef.current.saveTimeoutId = timeoutId;
  }, []);

  /**
   * Get the current scenario ID being managed
   */
  const getCurrentScenarioId = useCallback((): string | null => {
    return stateRef.current.currentScenarioId;
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelPendingOperations();
      resetAllStores();
    };
  }, [cancelPendingOperations, resetAllStores]);

  return {
    switchScenario,
    resetAllStores,
    cancelPendingOperations,
    isCurrentScenario,
    getAbortSignal,
    setSaveTimeout,
    getCurrentScenarioId,
  };
};

export default useScenarioLifecycle;
