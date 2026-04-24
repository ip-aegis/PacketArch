/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Hook for command palette interaction state:
 * keyboard navigation, query, highlighted index, execute + close, recently used tracking.
 */

import { useState, useCallback, useEffect } from 'react';
import { useUIStore } from '../../stores/uiStore';
import type { CommandDefinition } from './types';

// ── Recently used tracking (localStorage) ────────────────────

const STORAGE_KEY = 'packetarch-cmd-palette-recent';
const MAX_RECENT = 5;

export function getRecentCommandIds(): string[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

function trackRecentCommand(id: string): void {
  const recent = getRecentCommandIds().filter((r) => r !== id);
  recent.unshift(id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(recent.slice(0, MAX_RECENT)));
}

// ── Hook ─────────────────────────────────────────────────────

export function useCommandPalette(commands: CommandDefinition[]) {
  const [query, setQuery] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const isOpen = useUIStore((s) => s.commandPaletteOpen);
  const close = useUIStore((s) => s.closeCommandPalette);

  // Reset state when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setHighlightedIndex(0);
    }
  }, [isOpen]);

  // Clamp highlighted index when command list changes
  useEffect(() => {
    setHighlightedIndex((i) => Math.min(i, Math.max(0, commands.length - 1)));
  }, [commands.length]);

  const executeCommand = useCallback(
    (cmd: CommandDefinition) => {
      close();
      // Delay execute slightly so the palette closes first (avoids focus issues)
      requestAnimationFrame(() => {
        cmd.execute();
        // Only track non-device-search commands
        if (!cmd.id.startsWith('device:')) {
          trackRecentCommand(cmd.id);
        }
      });
    },
    [close],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setHighlightedIndex((i) => (i + 1) % Math.max(1, commands.length));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setHighlightedIndex((i) => (i - 1 + commands.length) % Math.max(1, commands.length));
          break;
        case 'Enter':
          e.preventDefault();
          if (commands[highlightedIndex]) {
            executeCommand(commands[highlightedIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          close();
          break;
      }
    },
    [commands, highlightedIndex, executeCommand, close],
  );

  return {
    query,
    setQuery,
    highlightedIndex,
    handleKeyDown,
    executeCommand,
    isOpen,
    close,
  };
}
