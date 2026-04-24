/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * History state management with Zustand
 * Implements undo/redo functionality using the command pattern
 * Now includes scenario-scoped commands to prevent cross-scenario undo/redo
 */

import { create } from 'zustand';
import { useScenarioStore } from './scenarioStore';

export interface HistoryCommand {
  type: string;
  undo: () => void;
  redo: () => void;
  timestamp: number;
  scenarioId?: string; // Track which scenario this command belongs to
}

interface HistoryState {
  past: HistoryCommand[];
  future: HistoryCommand[];
  maxHistory: number;
  currentScenarioId: string | null;

  // Actions
  push: (command: HistoryCommand) => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  clear: () => void;
  setScenarioId: (id: string | null) => void;
}

export const useHistoryStore = create<HistoryState>((set, get) => ({
  past: [],
  future: [],
  maxHistory: 50,
  currentScenarioId: null,

  push: (command) =>
    set((state) => {
      // Get current scenario ID from scenario store
      const currentScenarioId = useScenarioStore.getState().id;

      // Reject commands if no scenario is loaded or scenario mismatch
      if (!currentScenarioId) {
        console.warn('History command rejected: no scenario loaded');
        return state;
      }

      // Tag command with scenario ID
      const taggedCommand = {
        ...command,
        scenarioId: currentScenarioId,
      };

      // Add to past, clear future
      const newPast = [...state.past, taggedCommand];

      // Enforce max history
      const trimmedPast = newPast.length > state.maxHistory
        ? newPast.slice(newPast.length - state.maxHistory)
        : newPast;

      return {
        past: trimmedPast,
        future: [],
        currentScenarioId,
      };
    }),

  undo: () => {
    const { past, future } = get();
    if (past.length === 0) return;

    const command = past[past.length - 1];

    // Verify command is for current scenario
    const currentScenarioId = useScenarioStore.getState().id;
    if (command.scenarioId && command.scenarioId !== currentScenarioId) {
      console.warn('Undo rejected: command is for a different scenario');
      return;
    }

    const newPast = past.slice(0, -1);

    // Execute undo
    command.undo();

    set({
      past: newPast,
      future: [command, ...future],
    });
  },

  redo: () => {
    const { past, future } = get();
    if (future.length === 0) return;

    const command = future[0];

    // Verify command is for current scenario
    const currentScenarioId = useScenarioStore.getState().id;
    if (command.scenarioId && command.scenarioId !== currentScenarioId) {
      console.warn('Redo rejected: command is for a different scenario');
      return;
    }

    const newFuture = future.slice(1);

    // Execute redo
    command.redo();

    set({
      past: [...past, command],
      future: newFuture,
    });
  },

  canUndo: () => {
    const { past } = get();
    if (past.length === 0) return false;

    // Only allow undo if the last command is for the current scenario
    const lastCommand = past[past.length - 1];
    const currentScenarioId = useScenarioStore.getState().id;
    return !lastCommand.scenarioId || lastCommand.scenarioId === currentScenarioId;
  },

  canRedo: () => {
    const { future } = get();
    if (future.length === 0) return false;

    // Only allow redo if the next command is for the current scenario
    const nextCommand = future[0];
    const currentScenarioId = useScenarioStore.getState().id;
    return !nextCommand.scenarioId || nextCommand.scenarioId === currentScenarioId;
  },

  clear: () =>
    set({
      past: [],
      future: [],
      currentScenarioId: null,
    }),

  setScenarioId: (id) =>
    set({
      currentScenarioId: id,
    }),
}));

export default useHistoryStore;
