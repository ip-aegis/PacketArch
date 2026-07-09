/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 left rail — the device palette. Two ways to place a device:
 * drag onto the canvas, or CLICK to arm then click the canvas (the v1
 * palette was drag-only — unusable on a touchpad).
 */

import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listPaletteDevices } from '../../api/fingerprints';
import type { PaletteDeviceResponse } from '../../api/fingerprints';
import {
  DeviceCategory,
  DEVICE_CATEGORY_LABELS,
  CATEGORY_ORDER,
  getDeviceTypeMeta,
} from '../../constants/deviceTypeRegistry';
import { DeviceGlyph } from '../glyphs';
import { useStudio2UI } from '../uiState';
import { SURFACE, TEXT, ACCENT, ACCENT_SOFT, FONT } from '../tokens';

const RAIL_WIDTH = 248;

const PaletteRow: React.FC<{ item: PaletteDeviceResponse }> = ({ item }) => {
  const armedTemplate = useStudio2UI((s) => s.armedTemplate);
  const setArmedTemplate = useStudio2UI((s) => s.setArmedTemplate);
  const armed = armedTemplate?.id === item.id;
  const [hover, setHover] = useState(false);

  return (
    <div
      role="button"
      tabIndex={0}
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData('application/json', JSON.stringify(item));
        e.dataTransfer.effectAllowed = 'copy';
      }}
      onClick={() => setArmedTemplate(armed ? null : item)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          setArmedTemplate(armed ? null : item);
        }
      }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title={`${item.name} — drag to canvas, or click then click the canvas`}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 9,
        padding: '5px 10px',
        borderRadius: 6,
        cursor: 'grab',
        background: armed ? ACCENT_SOFT : hover ? SURFACE.hover : 'transparent',
        outline: armed ? `1px solid ${ACCENT}` : 'none',
      }}
    >
      <div
        style={{
          flex: '0 0 auto',
          width: 26,
          height: 26,
          borderRadius: 6,
          background: SURFACE.iconWell,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <DeviceGlyph deviceType={item.device_type} size={16} />
      </div>
      <div style={{ minWidth: 0 }}>
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: TEXT.primary,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {item.name}
        </div>
        <div
          style={{
            fontFamily: FONT.mono,
            fontSize: 9.5,
            color: TEXT.faint,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {getDeviceTypeMeta(item.device_type).label}
          {item.vendor_fingerprint?.fingerprint_vendor
            ? ` · ${item.vendor_fingerprint.fingerprint_vendor}`
            : ''}
        </div>
      </div>
    </div>
  );
};

const Rail: React.FC = () => {
  const [search, setSearch] = useState('');
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const armedTemplate = useStudio2UI((s) => s.armedTemplate);
  const zoneArmed = useStudio2UI((s) => s.zoneArmed);
  const setZoneArmed = useStudio2UI((s) => s.setZoneArmed);
  const conduitArmed = useStudio2UI((s) => s.conduitArmed);
  const setConduitArmed = useStudio2UI((s) => s.setConduitArmed);
  const conduitSourceZoneId = useStudio2UI((s) => s.conduitSourceZoneId);

  const { data, isLoading } = useQuery({
    queryKey: ['studio2-palette'],
    queryFn: () => listPaletteDevices({ page_size: 500 }),
    staleTime: 5 * 60 * 1000,
  });

  const groups = useMemo(() => {
    const items = data?.items ?? [];
    const q = search.trim().toLowerCase();
    const filtered = q
      ? items.filter(
          (i) =>
            i.name.toLowerCase().includes(q) ||
            i.device_type.toLowerCase().includes(q) ||
            (i.role ?? '').toLowerCase().includes(q) ||
            (i.vendor_fingerprint?.fingerprint_vendor ?? '').toLowerCase().includes(q),
        )
      : items;
    const byCategory = new Map<DeviceCategory, PaletteDeviceResponse[]>();
    for (const item of filtered) {
      const category = getDeviceTypeMeta(item.device_type).category;
      const list = byCategory.get(category) ?? [];
      list.push(item);
      byCategory.set(category, list);
    }
    return CATEGORY_ORDER.filter((c) => byCategory.has(c)).map(
      (c) => [c, byCategory.get(c)!] as const,
    );
  }, [data, search]);

  const toggleGroup = (key: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return (
    <div
      style={{
        width: RAIL_WIDTH,
        flex: `0 0 ${RAIL_WIDTH}px`,
        display: 'flex',
        flexDirection: 'column',
        background: SURFACE.chrome,
        borderRight: `1px solid ${SURFACE.border}`,
        fontFamily: FONT.ui,
        minHeight: 0,
      }}
    >
      <div style={{ padding: '10px 10px 8px' }}>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search devices…"
          aria-label="Search device templates"
          style={{
            width: '100%',
            boxSizing: 'border-box',
            background: SURFACE.raised,
            border: `1px solid ${SURFACE.border}`,
            borderRadius: 6,
            color: TEXT.primary,
            fontFamily: FONT.ui,
            fontSize: 12.5,
            padding: '6px 10px',
            outline: 'none',
          }}
        />
      </div>

      <div style={{ padding: '0 10px 8px', display: 'flex', gap: 6 }}>
        <button
          onClick={() => setZoneArmed(!zoneArmed)}
          aria-pressed={zoneArmed}
          title="Click, then click the canvas to place a zone — resize it with the handles"
          style={{
            flex: 1,
            background: zoneArmed ? ACCENT_SOFT : SURFACE.raised,
            border: `1px solid ${zoneArmed ? ACCENT : SURFACE.border}`,
            borderRadius: 6,
            color: zoneArmed ? ACCENT : TEXT.secondary,
            fontFamily: FONT.ui,
            fontSize: 12,
            fontWeight: 600,
            padding: '6px 8px',
            cursor: 'pointer',
          }}
        >
          ▭ Zone
        </button>
        <button
          onClick={() => setConduitArmed(!conduitArmed)}
          aria-pressed={conduitArmed}
          title="Click, then click two zones to connect them with an IEC 62443 conduit"
          style={{
            flex: 1,
            background: conduitArmed ? ACCENT_SOFT : SURFACE.raised,
            border: `1px solid ${conduitArmed ? ACCENT : SURFACE.border}`,
            borderRadius: 6,
            color: conduitArmed ? ACCENT : TEXT.secondary,
            fontFamily: FONT.ui,
            fontSize: 12,
            fontWeight: 600,
            padding: '6px 8px',
            cursor: 'pointer',
          }}
        >
          ⛨ Conduit
        </button>
      </div>

      {(armedTemplate || zoneArmed || conduitArmed) && (
        <div
          style={{
            margin: '0 10px 8px',
            padding: '6px 10px',
            borderRadius: 6,
            background: ACCENT_SOFT,
            color: ACCENT,
            fontSize: 11.5,
            lineHeight: 1.4,
          }}
        >
          {armedTemplate ? (
            <>
              Click the canvas to place <b>{armedTemplate.name}</b> — Esc to cancel
            </>
          ) : conduitArmed ? (
            conduitSourceZoneId ? (
              <>Now click the second zone — Esc to cancel</>
            ) : (
              <>Click the first zone to connect — Esc to cancel</>
            )
          ) : (
            <>Click the canvas to place a zone — Esc to cancel</>
          )}
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 6px 10px' }}>
        {isLoading && (
          <div style={{ color: TEXT.faint, fontSize: 12, padding: '8px 10px' }}>Loading palette…</div>
        )}
        {groups.map(([category, items]) => {
          const isCollapsed = collapsed.has(category);
          return (
            <div key={category}>
              <button
                onClick={() => toggleGroup(category)}
                aria-expanded={!isCollapsed}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  width: '100%',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '8px 10px 4px',
                  fontFamily: FONT.mono,
                  fontSize: 10,
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  color: TEXT.muted,
                  textAlign: 'left',
                }}
              >
                <span style={{ fontSize: 8 }}>{isCollapsed ? '▸' : '▾'}</span>
                {DEVICE_CATEGORY_LABELS[category]}
                <span style={{ marginLeft: 'auto', color: TEXT.faint }}>{items.length}</span>
              </button>
              {!isCollapsed && items.map((item) => <PaletteRow key={item.id} item={item} />)}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Rail;
