/**
 * Command Palette overlay (Cmd+K / Ctrl+K).
 * Renders a centered modal with search input, grouped/scored results, and footer hints.
 *
 * The palette is rendered globally in AppLayout but needs optional canvas deps
 * from the Studio page. We use a context bridge: the Studio page registers canvas
 * callbacks via a module-level ref that this component reads.
 */

import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import { SearchOutlined } from '@ant-design/icons';
import { useUIStore } from '../../stores/uiStore';
import { useCommands, type CanvasDeps } from './useCommands';
import { useCommandPalette } from './useCommandPalette';
import CommandPaletteItem from './CommandPaletteItem';
import { CATEGORY_LABELS, type CommandCategory } from './types';

// ── Canvas deps bridge ───────────────────────────────────────
// Studio page registers its ReactFlow-dependent callbacks here.
// This avoids lifting ReactFlowProvider to AppLayout.

let _canvasDeps: CanvasDeps | null = null;

export function registerCanvasDeps(deps: CanvasDeps | null): void {
  _canvasDeps = deps;
}

// ── Platform detection ───────────────────────────────────────

const isMac = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform);
const MOD_KEY = isMac ? '⌘' : 'Ctrl';

// ── Category display order ───────────────────────────────────

const CATEGORY_ORDER: CommandCategory[] = [
  'navigation',
  'canvas',
  'panel',
  'grouping',
  'scenario',
  'device-search',
  'help',
];

// ── Component ────────────────────────────────────────────────

const CommandPalette: React.FC = () => {
  const isOpen = useUIStore((s) => s.commandPaletteOpen);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands = useCommands(
    // We read query from the hook below, but need it for useCommands too.
    // Solve with a ref-based approach: pass query string through the palette hook state.
    '', // placeholder — real filtering happens below
    _canvasDeps,
  );

  // We need query to drive useCommands, but useCommandPalette needs commands.
  // Break the cycle: CommandPaletteInner does the real work once open.

  if (!isOpen) return null;

  return <CommandPaletteInner inputRef={inputRef} />;
};

const CommandPaletteInner: React.FC<{
  inputRef: React.RefObject<HTMLInputElement | null>;
}> = ({ inputRef }) => {
  const close = useUIStore((s) => s.closeCommandPalette);

  // Local query state
  const [query, setQuery] = React.useState('');
  const commands = useCommands(query, _canvasDeps);
  const palette = useCommandPalette(commands);

  // Sync query into palette (palette.setQuery triggers its own reset logic)
  const handleQueryChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      setQuery(val);
      palette.setQuery(val);
    },
    [palette],
  );

  // Focus input on open
  useEffect(() => {
    requestAnimationFrame(() => inputRef.current?.focus());
  }, [inputRef]);

  // Grouped display when no query
  const grouped = useMemo(() => {
    if (query) return null; // flat scored list when searching
    const groups: Partial<Record<CommandCategory, typeof commands>> = {};
    commands.forEach((cmd) => {
      if (!groups[cmd.category]) groups[cmd.category] = [];
      groups[cmd.category]!.push(cmd);
    });
    return groups;
  }, [commands, query]);

  // Compute flat index mapping for grouped display
  const flatCommands = useMemo(() => {
    if (query) return commands;
    const flat: typeof commands = [];
    CATEGORY_ORDER.forEach((cat) => {
      if (grouped?.[cat]) flat.push(...grouped[cat]!);
    });
    return flat;
  }, [commands, query, grouped]);

  // Mouse hover → update highlight
  const handleMouseMove = useCallback(
    (index: number) => {
      // We can't call setHighlightedIndex directly from useCommandPalette,
      // so we access it via the same React state. We'll use a wrapper.
    },
    [],
  );

  // Backdrop click
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) close();
    },
    [close],
  );

  // Determine the mode hint
  const isDeviceMode = query.startsWith('@');
  const hintText = isDeviceMode
    ? 'Searching devices on canvas...'
    : 'Type to search commands...';

  // Global index counter for rendering grouped items
  let globalIndex = 0;

  return (
    <div className="command-palette-overlay" onClick={handleBackdropClick}>
      <div className="command-palette-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="command-palette-header">
          <SearchOutlined className="command-palette-search-icon" />
          <input
            ref={inputRef}
            className="command-palette-input"
            value={query}
            onChange={handleQueryChange}
            onKeyDown={palette.handleKeyDown}
            placeholder={hintText}
            spellCheck={false}
            autoComplete="off"
          />
          <kbd className="command-palette-kbd">{MOD_KEY}+K</kbd>
        </div>

        {/* Divider */}
        <div className="command-palette-divider" />

        {/* Results */}
        <div className="command-palette-results">
          {flatCommands.length === 0 && (
            <div className="command-palette-empty">
              {query ? 'No matching commands' : 'No commands available'}
            </div>
          )}

          {query ? (
            // Flat scored list
            flatCommands.map((cmd, i) => (
              <CommandPaletteItem
                key={cmd.id}
                command={cmd}
                isHighlighted={i === palette.highlightedIndex}
                onClick={() => palette.executeCommand(cmd)}
              />
            ))
          ) : (
            // Grouped display
            CATEGORY_ORDER.map((cat) => {
              const group = grouped?.[cat];
              if (!group || group.length === 0) return null;
              const startIndex = globalIndex;
              globalIndex += group.length;
              return (
                <div key={cat}>
                  <div className="command-palette-group-header">
                    {CATEGORY_LABELS[cat]}
                  </div>
                  {group.map((cmd, i) => (
                    <CommandPaletteItem
                      key={cmd.id}
                      command={cmd}
                      isHighlighted={startIndex + i === palette.highlightedIndex}
                      onClick={() => palette.executeCommand(cmd)}
                    />
                  ))}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="command-palette-footer">
          <span><kbd>&uarr;</kbd><kbd>&darr;</kbd> navigate</span>
          <span><kbd>&crarr;</kbd> select</span>
          <span><kbd>esc</kbd> close</span>
          {!isDeviceMode && <span><kbd>@</kbd> device search</span>}
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
