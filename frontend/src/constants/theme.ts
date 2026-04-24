/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Theme color constants for inline JS styles.
 *
 * These complement the CSS custom properties in index.css.
 * Use these when applying colors in React inline styles;
 * use the CSS variables (var(--bg-primary) etc.) in CSS classes.
 */

// ── Text Colors ──────────────────────────────────────────────
export const TEXT_PRIMARY = '#ffffff';
export const TEXT_HEADING = '#e0e8f0';
export const TEXT_BODY = '#c9d1d9';
export const TEXT_PARAGRAPH = '#8aa4bc';
export const TEXT_MUTED = '#6a8caf';

// ── Background Colors ────────────────────────────────────────
export const BG_PANEL = '#1a2734';
export const BG_CARD = '#1e2d3d';
export const BG_INSET = '#152330';
export const BG_TOOLBAR = '#253545';
export const BG_CODE = '#0d1117';

// ── Border Colors ────────────────────────────────────────────
export const BORDER_DEFAULT = '#2a3f54';
export const BORDER_ELEVATED = '#2d2d52';
export const BORDER_CODE = '#30363d';

// ── Accent Colors ────────────────────────────────────────────
export const ACCENT_BLUE = '#049FD9';
export const ACCENT_BLUE_HOVER = '#5a9fd4';
export const ACCENT_GREEN = '#52c41a';

// ── Composite Styles ─────────────────────────────────────────

/** Standard dark card: bg + border (most common inline pattern). */
export const CARD_STYLE = {
  background: BG_CARD,
  border: `1px solid ${BORDER_DEFAULT}`,
} as const;

/** Code block styling. */
export const CODE_BLOCK_STYLE = {
  background: BG_CODE,
  border: `1px solid ${BORDER_CODE}`,
  borderRadius: 6,
  padding: 12,
  overflow: 'auto' as const,
  fontSize: 13,
  fontFamily: 'monospace',
} as const;
