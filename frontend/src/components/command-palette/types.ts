/**
 * Command Palette types
 */

import type { ReactNode } from 'react';

export type CommandCategory =
  | 'navigation'
  | 'canvas'
  | 'panel'
  | 'grouping'
  | 'scenario'
  | 'device-search'
  | 'help';

export type CommandContext = 'global' | 'studio' | 'studio-with-selection';

export interface CommandDefinition {
  id: string;
  label: string;
  category: CommandCategory;
  context: CommandContext;
  icon: ReactNode;
  shortcut?: string;
  keywords?: string[];
  disabled?: boolean;
  execute: () => void;
}

export const CATEGORY_LABELS: Record<CommandCategory, string> = {
  navigation: 'Navigate',
  canvas: 'Canvas',
  panel: 'Panel',
  grouping: 'Group',
  scenario: 'Scenario',
  'device-search': 'Device',
  help: 'Help',
};

export const CATEGORY_COLORS: Record<CommandCategory, string> = {
  navigation: '#049FD9',
  canvas: '#6CC04A',
  panel: '#FBAB18',
  grouping: '#00BCEB',
  scenario: '#9C27B0',
  'device-search': '#00BCEB',
  help: '#a8a8c0',
};
