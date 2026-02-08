/**
 * Single result row in the command palette.
 * Shows: icon | label | category tag + shortcut badge
 */

import React, { useRef, useEffect } from 'react';
import type { CommandDefinition } from './types';
import { CATEGORY_LABELS, CATEGORY_COLORS } from './types';

interface Props {
  command: CommandDefinition;
  isHighlighted: boolean;
  onClick: () => void;
}

const CommandPaletteItem: React.FC<Props> = ({ command, isHighlighted, onClick }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isHighlighted && ref.current) {
      ref.current.scrollIntoView({ block: 'nearest' });
    }
  }, [isHighlighted]);

  const categoryColor = CATEGORY_COLORS[command.category];
  const categoryLabel = CATEGORY_LABELS[command.category];

  // For device search, show extra info from keywords (type, vendor, IP)
  const subtitle =
    command.category === 'device-search' && command.keywords
      ? command.keywords.filter(Boolean).join(' · ')
      : undefined;

  return (
    <div
      ref={ref}
      className={`command-palette-item${isHighlighted ? ' highlighted' : ''}`}
      onClick={onClick}
      onMouseEnter={(e) => {
        // Parent handles highlight-on-hover via onMouseMove on the list
      }}
    >
      <div className="command-palette-item-left">
        {command.icon && (
          <span className="command-palette-item-icon">{command.icon}</span>
        )}
        <div className="command-palette-item-text">
          <span className="command-palette-item-label">{command.label}</span>
          {subtitle && (
            <span className="command-palette-item-subtitle">{subtitle}</span>
          )}
        </div>
      </div>

      <div className="command-palette-item-right">
        <span
          className="command-palette-item-category"
          style={{ color: categoryColor, borderColor: categoryColor + '40' }}
        >
          {categoryLabel}
        </span>
        {command.shortcut && (
          <span className="command-palette-item-shortcut">{command.shortcut}</span>
        )}
      </div>
    </div>
  );
};

export default React.memo(CommandPaletteItem);
