/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 inspector — selection-driven right panel. One thing at a time:
 * the selected device, the selected flow, or (nothing selected) scenario
 * settings. All edits dispatch through the command bus, so every keystroke
 * is undoable; per-entity coalescing folds a typing burst into one step.
 */

import React from 'react';
import { useDocumentStore, commands } from '../document/documentStore';
import { DeviceGlyph } from '../glyphs';
import { getDeviceTypeMeta } from '../../constants/deviceTypeRegistry';
import { PROTOCOL_EDGE_LABELS } from '../../constants/protocols';
import type { ProtocolType } from '../../types';
import { SURFACE, TEXT, FONT, protocolEdgeColor } from '../tokens';

const INSPECTOR_WIDTH = 296;

// ---------------------------------------------------------------------------
// Field primitives (token-styled)
// ---------------------------------------------------------------------------

const fieldLabel: React.CSSProperties = {
  display: 'block',
  fontFamily: FONT.mono,
  fontSize: 9.5,
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: TEXT.muted,
  marginBottom: 4,
};

const fieldInput: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  background: SURFACE.raised,
  border: `1px solid ${SURFACE.border}`,
  borderRadius: 6,
  color: TEXT.primary,
  fontFamily: FONT.ui,
  fontSize: 12.5,
  padding: '6px 9px',
  outline: 'none',
};

const Field: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <label style={{ display: 'block', marginBottom: 12 }}>
    <span style={fieldLabel}>{label}</span>
    {children}
  </label>
);

const SectionTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div
    style={{
      fontFamily: FONT.mono,
      fontSize: 10,
      letterSpacing: '0.12em',
      textTransform: 'uppercase',
      color: TEXT.faint,
      borderBottom: `1px solid ${SURFACE.border}`,
      padding: '14px 0 5px',
      marginBottom: 12,
    }}
  >
    {children}
  </div>
);

// ---------------------------------------------------------------------------
// Device form
// ---------------------------------------------------------------------------

const DeviceForm: React.FC<{ deviceId: string }> = ({ deviceId }) => {
  const device = useDocumentStore((s) => s.doc?.devices[deviceId]);
  const zones = useDocumentStore((s) => s.doc?.zones);
  if (!device) return null;

  const dispatchUpdate = (updates: Parameters<typeof commands.updateDevice>[2]) => {
    const state = useDocumentStore.getState();
    if (!state.doc) return;
    const cmd = commands.updateDevice(state.doc, deviceId, updates);
    if (cmd) state.dispatch(cmd);
  };

  const typeMeta = getDeviceTypeMeta(device.type);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
        <div
          style={{
            width: 34,
            height: 34,
            borderRadius: 8,
            background: SURFACE.iconWell,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flex: '0 0 auto',
          }}
        >
          <DeviceGlyph deviceType={device.type} size={20} />
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 650, color: TEXT.primary }}>{typeMeta.label}</div>
          <div style={{ fontFamily: FONT.mono, fontSize: 10, color: TEXT.faint }}>
            {device.vendor ?? 'no vendor'}
            {device.fingerprintModel ? ` · ${device.fingerprintModel}` : ''}
          </div>
        </div>
      </div>

      <SectionTitle>Identity</SectionTitle>
      <Field label="Name">
        <input
          style={fieldInput}
          value={device.name}
          onChange={(e) => dispatchUpdate({ name: e.target.value })}
        />
      </Field>
      <Field label="Zone">
        <select
          style={{ ...fieldInput, appearance: 'auto' }}
          value={device.zoneId ?? ''}
          onChange={(e) => dispatchUpdate({ zoneId: e.target.value || undefined })}
        >
          <option value="">— none —</option>
          {Object.values(zones ?? {}).map((z) => (
            <option key={z.id} value={z.id}>
              {z.name}
            </option>
          ))}
        </select>
      </Field>

      <SectionTitle>Network</SectionTitle>
      <Field label="IP address">
        <input
          style={{ ...fieldInput, fontFamily: FONT.mono }}
          value={device.network?.ipAddress ?? ''}
          placeholder="auto-assigned"
          onChange={(e) =>
            dispatchUpdate({ network: { ...device.network, ipAddress: e.target.value } })
          }
        />
      </Field>
      {device.network?.macAddress ? (
        <Field label="MAC (from fingerprint)">
          <div style={{ ...fieldInput, background: 'transparent', color: TEXT.muted, fontFamily: FONT.mono }}>
            {device.network.macAddress}
          </div>
        </Field>
      ) : null}

      <SectionTitle>Protocols</SectionTitle>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
        {device.protocols.length === 0 && (
          <span style={{ fontSize: 11.5, color: TEXT.faint }}>none</span>
        )}
        {device.protocols.map((p) => (
          <span
            key={p}
            style={{
              fontFamily: FONT.mono,
              fontSize: 10,
              color: protocolEdgeColor(p),
              border: `1px solid ${SURFACE.border}`,
              borderRadius: 4,
              padding: '1px 6px',
            }}
          >
            {PROTOCOL_EDGE_LABELS[p as keyof typeof PROTOCOL_EDGE_LABELS] ?? p}
          </span>
        ))}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Flow form
// ---------------------------------------------------------------------------

const FlowForm: React.FC<{ flowId: string }> = ({ flowId }) => {
  const flow = useDocumentStore((s) => s.doc?.flows[flowId]);
  const doc = useDocumentStore((s) => s.doc);
  if (!flow || !doc) return null;

  const source = doc.devices[flow.sourceDeviceId];
  const target = doc.devices[flow.targetDeviceId];
  const options = Array.from(
    new Set([
      ...(source?.protocols ?? []),
      ...(target?.protocols ?? []),
      flow.protocol,
    ]),
  );

  const dispatchUpdate = (updates: Parameters<typeof commands.updateFlow>[2]) => {
    const state = useDocumentStore.getState();
    if (!state.doc) return;
    const cmd = commands.updateFlow(state.doc, flowId, updates);
    if (cmd) state.dispatch(cmd);
  };

  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 650, color: TEXT.primary, marginBottom: 2 }}>Flow</div>
      <div style={{ fontFamily: FONT.mono, fontSize: 10.5, color: TEXT.muted, marginBottom: 4 }}>
        {source?.name ?? '?'} → {target?.name ?? '?'}
      </div>

      <SectionTitle>Protocol</SectionTitle>
      <Field label="Protocol">
        <select
          style={{ ...fieldInput, appearance: 'auto' }}
          value={flow.protocol}
          onChange={(e) => dispatchUpdate({ protocol: e.target.value as ProtocolType })}
        >
          {options.map((p) => (
            <option key={p} value={p}>
              {PROTOCOL_EDGE_LABELS[p as keyof typeof PROTOCOL_EDGE_LABELS] ?? p}
            </option>
          ))}
        </select>
      </Field>

      <SectionTitle>Timing</SectionTitle>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Field label="Interval (ms)">
          <input
            type="number"
            style={{ ...fieldInput, fontFamily: FONT.mono }}
            value={flow.timing?.intervalMs ?? 1000}
            min={10}
            onChange={(e) =>
              dispatchUpdate({ timing: { ...flow.timing, intervalMs: Number(e.target.value) } })
            }
          />
        </Field>
        <Field label="Jitter (ms)">
          <input
            type="number"
            style={{ ...fieldInput, fontFamily: FONT.mono }}
            value={flow.timing?.jitterMs ?? 0}
            min={0}
            onChange={(e) =>
              dispatchUpdate({ timing: { ...flow.timing, jitterMs: Number(e.target.value) } })
            }
          />
        </Field>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Zone form
// ---------------------------------------------------------------------------

const ZONE_TYPES = ['vertical', 'network', 'vlan', 'logical'] as const;
const PURDUE_LEVELS = [0, 1, 2, 3, 3.5, 4] as const;

const ZoneForm: React.FC<{ zoneId: string }> = ({ zoneId }) => {
  const zone = useDocumentStore((s) => s.doc?.zones[zoneId]);
  const memberCount = useDocumentStore(
    (s) => Object.values(s.doc?.devices ?? {}).filter((d) => d.zoneId === zoneId).length,
  );
  if (!zone) return null;

  const dispatchUpdate = (updates: Parameters<typeof commands.updateZone>[2]) => {
    const state = useDocumentStore.getState();
    if (!state.doc) return;
    const cmd = commands.updateZone(state.doc, zoneId, updates);
    if (cmd) state.dispatch(cmd);
  };

  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 650, color: TEXT.primary, marginBottom: 2 }}>Zone</div>
      <div style={{ fontFamily: FONT.mono, fontSize: 10.5, color: TEXT.muted, marginBottom: 4 }}>
        {memberCount} device{memberCount === 1 ? '' : 's'} — drag devices in or out to change
        membership
      </div>

      <SectionTitle>Identity</SectionTitle>
      <Field label="Name">
        <input style={fieldInput} value={zone.name} onChange={(e) => dispatchUpdate({ name: e.target.value })} />
      </Field>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Field label="Type">
          <select
            style={{ ...fieldInput, appearance: 'auto' }}
            value={zone.type}
            onChange={(e) => dispatchUpdate({ type: e.target.value as typeof zone.type })}
          >
            {ZONE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Purdue level">
          <select
            style={{ ...fieldInput, appearance: 'auto' }}
            value={zone.level ?? ''}
            onChange={(e) =>
              dispatchUpdate({ level: e.target.value === '' ? undefined : Number(e.target.value) })
            }
          >
            <option value="">—</option>
            {PURDUE_LEVELS.map((l) => (
              <option key={l} value={l}>
                L{l}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <SectionTitle>Network</SectionTitle>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Field label="Subnet">
          <input
            style={{ ...fieldInput, fontFamily: FONT.mono }}
            value={zone.network?.subnet ?? ''}
            placeholder="10.x.y.0/24"
            onChange={(e) =>
              dispatchUpdate({ network: { ...zone.network, subnet: e.target.value } })
            }
          />
        </Field>
        <Field label="VLAN">
          <input
            type="number"
            style={{ ...fieldInput, fontFamily: FONT.mono }}
            value={zone.network?.vlanId ?? ''}
            onChange={(e) =>
              dispatchUpdate({
                network: {
                  subnet: zone.network?.subnet ?? '',
                  ...zone.network,
                  vlanId: e.target.value === '' ? undefined : Number(e.target.value),
                },
              })
            }
          />
        </Field>
      </div>

      <button
        onClick={() => {
          const state = useDocumentStore.getState();
          if (!state.doc) return;
          state.dispatch(commands.deleteZones(state.doc, [zoneId]));
          state.setSelection([], []);
        }}
        style={{
          marginTop: 8,
          background: 'transparent',
          border: `1px solid ${SURFACE.border}`,
          borderRadius: 6,
          color: TEXT.muted,
          fontFamily: FONT.ui,
          fontSize: 12,
          padding: '5px 12px',
          cursor: 'pointer',
        }}
      >
        Delete zone (keeps devices)
      </button>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Conduit info (editing arrives with the conduit tool)
// ---------------------------------------------------------------------------

const ConduitInfo: React.FC<{ conduitId: string }> = ({ conduitId }) => {
  const conduit = useDocumentStore((s) => s.doc?.conduits[conduitId]);
  const doc = useDocumentStore((s) => s.doc);
  if (!conduit || !doc) return null;
  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 650, color: TEXT.primary, marginBottom: 2 }}>
        Conduit
      </div>
      <div style={{ fontFamily: FONT.mono, fontSize: 10.5, color: TEXT.muted, marginBottom: 8 }}>
        {doc.zones[conduit.sourceZoneId]?.name ?? '?'} {conduit.direction === 'bidirectional' ? '↔' : '→'}{' '}
        {doc.zones[conduit.targetZoneId]?.name ?? '?'}
      </div>
      <SectionTitle>Allowed protocols</SectionTitle>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
        {(conduit.allowedProtocols ?? []).length === 0 && (
          <span style={{ fontSize: 11.5, color: TEXT.faint }}>none defined</span>
        )}
        {(conduit.allowedProtocols ?? []).map((p) => (
          <span
            key={p}
            style={{
              fontFamily: FONT.mono,
              fontSize: 10,
              color: protocolEdgeColor(p),
              border: `1px solid ${SURFACE.border}`,
              borderRadius: 4,
              padding: '1px 6px',
            }}
          >
            {PROTOCOL_EDGE_LABELS[p as keyof typeof PROTOCOL_EDGE_LABELS] ?? p}
          </span>
        ))}
      </div>
      <div style={{ fontSize: 11, color: TEXT.faint, marginTop: 12, lineHeight: 1.5 }}>
        Conduit editing (direction, protocols, SL) arrives with the conduit tool.
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Scenario settings (nothing selected)
// ---------------------------------------------------------------------------

const ScenarioForm: React.FC = () => {
  const meta = useDocumentStore((s) => s.doc?.meta);
  if (!meta) return null;

  const dispatchMeta = (updates: Partial<typeof meta>) => {
    const state = useDocumentStore.getState();
    if (!state.doc) return;
    state.dispatch(commands.setMeta(state.doc, updates));
  };

  return (
    <div>
      <div style={{ fontSize: 13, fontWeight: 650, color: TEXT.primary, marginBottom: 4 }}>
        Scenario
      </div>
      <SectionTitle>Settings</SectionTitle>
      <Field label="Name">
        <input style={fieldInput} value={meta.name} onChange={(e) => dispatchMeta({ name: e.target.value })} />
      </Field>
      <Field label="Description">
        <textarea
          style={{ ...fieldInput, minHeight: 90, resize: 'vertical' }}
          value={meta.description}
          onChange={(e) => dispatchMeta({ description: e.target.value })}
        />
      </Field>
      <div style={{ fontSize: 11, color: TEXT.faint, lineHeight: 1.5 }}>
        Select a device or flow to edit it here. Modes, phases, and health land in the next
        phases of the v2 build.
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------

const Inspector: React.FC = () => {
  const selection = useDocumentStore((s) => s.selection);
  const doc = useDocumentStore((s) => s.doc);
  const total = selection.deviceIds.length + selection.edgeIds.length;

  let body: React.ReactNode;
  if (total > 1) {
    body = (
      <div style={{ fontSize: 12, color: TEXT.muted }}>
        {total} items selected — bulk editing lands later.
      </div>
    );
  } else if (selection.deviceIds.length === 1) {
    const nodeId = selection.deviceIds[0];
    if (doc?.devices[nodeId]) body = <DeviceForm deviceId={nodeId} />;
    else if (doc?.zones[nodeId]) body = <ZoneForm zoneId={nodeId} />;
    else body = <ScenarioForm />;
  } else if (selection.edgeIds.length === 1) {
    const edgeId = selection.edgeIds[0];
    if (doc?.flows[edgeId]) body = <FlowForm flowId={edgeId} />;
    else if (doc?.conduits[edgeId]) body = <ConduitInfo conduitId={edgeId} />;
    else body = <ScenarioForm />;
  } else {
    body = <ScenarioForm />;
  }

  return (
    <div
      style={{
        width: INSPECTOR_WIDTH,
        flex: `0 0 ${INSPECTOR_WIDTH}px`,
        overflowY: 'auto',
        background: SURFACE.chrome,
        borderLeft: `1px solid ${SURFACE.border}`,
        padding: '14px 16px',
        fontFamily: FONT.ui,
        minHeight: 0,
      }}
    >
      {body}
    </div>
  );
};

export default Inspector;
