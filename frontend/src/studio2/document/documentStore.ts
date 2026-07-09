/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 scenario document store + command bus.
 *
 * Every mutation flows through `dispatch(command)`. A command is a list of
 * entity-level before/after snapshots, so its inverse is derivable by
 * construction — undo coverage is a property of the bus, not of call-site
 * discipline. Cascades (e.g. device delete removing its flows) are captured
 * because command BUILDERS enumerate every affected entity up front.
 *
 * Commands with the same `coalesceKey` arriving within COALESCE_WINDOW_MS
 * merge into one undo step (drag streams become a single "Move").
 */

import { create } from 'zustand';
import type {
  ScenarioDevice,
  ScenarioFlow,
  ScenarioZone,
  ScenarioConduit,
  Phase,
  CellIsolationConfig,
  VerticalType,
} from '../../types';

// ---------------------------------------------------------------------------
// Document shape
// ---------------------------------------------------------------------------

export interface ScenarioMeta {
  id: string;
  name: string;
  description: string;
  vertical?: VerticalType;
  totalDurationMs?: number;
  cellIsolation?: CellIsolationConfig;
  broadcastTrafficEnabled?: boolean;
  cleanDemoMode?: boolean;
}

export interface ScenarioDocument {
  meta: ScenarioMeta;
  devices: Record<string, ScenarioDevice>;
  flows: Record<string, ScenarioFlow>;
  zones: Record<string, ScenarioZone>;
  conduits: Record<string, ScenarioConduit>;
  phases: Phase[];
  addressing: { ipRange?: string; autoAssignEnabled?: boolean } | null;
  /**
   * Definition keys v2 doesn't model (yet). Round-tripped verbatim by the
   * codec so a v2 save can never wipe fields another surface wrote.
   */
  definitionExtras: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

export type EntityKind = 'device' | 'flow' | 'zone' | 'conduit';

type EntityOf<K extends EntityKind> = K extends 'device'
  ? ScenarioDevice
  : K extends 'flow'
    ? ScenarioFlow
    : K extends 'zone'
      ? ScenarioZone
      : ScenarioConduit;

export interface EntityMutation<K extends EntityKind = EntityKind> {
  kind: K;
  id: string;
  /** Snapshot before the command. undefined = entity did not exist. */
  before?: EntityOf<K>;
  /** Snapshot after the command. undefined = entity is deleted. */
  after?: EntityOf<K>;
}

export interface MetaMutation {
  kind: 'meta';
  before: Partial<ScenarioMeta>;
  after: Partial<ScenarioMeta>;
}

export interface PhasesMutation {
  kind: 'phases';
  before: Phase[];
  after: Phase[];
}

export type Mutation = EntityMutation | MetaMutation | PhasesMutation;

export interface Command {
  /** Human-readable label ("Delete 3 devices") for history UI. */
  label: string;
  mutations: Mutation[];
  /** Same key within the window ⇒ merge into the previous undo step. */
  coalesceKey?: string;
  at: number;
}

const COALESCE_WINDOW_MS = 900;
const MAX_HISTORY = 100;

const ENTITY_MAP: Record<EntityKind, keyof Pick<ScenarioDocument, 'devices' | 'flows' | 'zones' | 'conduits'>> = {
  device: 'devices',
  flow: 'flows',
  zone: 'zones',
  conduit: 'conduits',
};

function applyMutations(doc: ScenarioDocument, mutations: Mutation[], direction: 'after' | 'before'): ScenarioDocument {
  const next: ScenarioDocument = {
    ...doc,
    devices: { ...doc.devices },
    flows: { ...doc.flows },
    zones: { ...doc.zones },
    conduits: { ...doc.conduits },
  };
  for (const m of mutations) {
    if (m.kind === 'meta') {
      next.meta = { ...next.meta, ...(direction === 'after' ? m.after : m.before) };
    } else if (m.kind === 'phases') {
      next.phases = direction === 'after' ? m.after : m.before;
    } else {
      const map = next[ENTITY_MAP[m.kind]] as Record<string, unknown>;
      const value = direction === 'after' ? m.after : m.before;
      if (value === undefined) {
        delete map[m.id];
      } else {
        map[m.id] = value;
      }
    }
  }
  return next;
}

/** Merge b into a: keep a's `before`s, take b's `after`s, append new ones. */
function coalesce(a: Command, b: Command): Command {
  const merged = [...a.mutations];
  for (const mb of b.mutations) {
    if (mb.kind === 'meta' || mb.kind === 'phases') {
      merged.push(mb);
      continue;
    }
    const idx = merged.findIndex(
      (ma) => ma.kind === mb.kind && (ma as EntityMutation).id === mb.id,
    );
    if (idx >= 0) {
      const ma = merged[idx] as EntityMutation;
      merged[idx] = { ...ma, after: mb.after } as EntityMutation;
    } else {
      merged.push(mb);
    }
  }
  return { ...a, mutations: merged, at: b.at };
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

interface DocumentState {
  doc: ScenarioDocument | null;
  dirty: boolean;
  undoStack: Command[];
  redoStack: Command[];
  selection: { deviceIds: string[]; edgeIds: string[] };

  loadDocument: (doc: ScenarioDocument) => void;
  closeDocument: () => void;
  dispatch: (command: Omit<Command, 'at'>) => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  markSaved: () => void;
  setSelection: (deviceIds: string[], edgeIds: string[]) => void;
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  doc: null,
  dirty: false,
  undoStack: [],
  redoStack: [],
  selection: { deviceIds: [], edgeIds: [] },

  loadDocument: (doc) =>
    set({ doc, dirty: false, undoStack: [], redoStack: [], selection: { deviceIds: [], edgeIds: [] } }),

  closeDocument: () =>
    set({ doc: null, dirty: false, undoStack: [], redoStack: [], selection: { deviceIds: [], edgeIds: [] } }),

  dispatch: (command) =>
    set((state) => {
      if (!state.doc || command.mutations.length === 0) return state;
      const cmd: Command = { ...command, at: Date.now() };
      const doc = applyMutations(state.doc, cmd.mutations, 'after');

      const top = state.undoStack[state.undoStack.length - 1];
      const undoStack =
        top &&
        cmd.coalesceKey &&
        top.coalesceKey === cmd.coalesceKey &&
        cmd.at - top.at < COALESCE_WINDOW_MS
          ? [...state.undoStack.slice(0, -1), coalesce(top, cmd)]
          : [...state.undoStack.slice(-(MAX_HISTORY - 1)), cmd];

      return { doc, undoStack, redoStack: [], dirty: true };
    }),

  undo: () =>
    set((state) => {
      const cmd = state.undoStack[state.undoStack.length - 1];
      if (!cmd || !state.doc) return state;
      return {
        doc: applyMutations(state.doc, cmd.mutations, 'before'),
        undoStack: state.undoStack.slice(0, -1),
        redoStack: [...state.redoStack, cmd],
        dirty: true,
      };
    }),

  redo: () =>
    set((state) => {
      const cmd = state.redoStack[state.redoStack.length - 1];
      if (!cmd || !state.doc) return state;
      return {
        doc: applyMutations(state.doc, cmd.mutations, 'after'),
        redoStack: state.redoStack.slice(0, -1),
        undoStack: [...state.undoStack, cmd],
        dirty: true,
      };
    }),

  canUndo: () => get().undoStack.length > 0,
  canRedo: () => get().redoStack.length > 0,
  markSaved: () => set({ dirty: false }),
  setSelection: (deviceIds, edgeIds) => set({ selection: { deviceIds, edgeIds } }),
}));

// ---------------------------------------------------------------------------
// Command builders — every affected entity is enumerated here, so undo
// captures cascades automatically.
// ---------------------------------------------------------------------------

export const commands = {
  addDevice(device: ScenarioDevice): Omit<Command, 'at'> {
    return {
      label: `Add ${device.name}`,
      mutations: [{ kind: 'device', id: device.id, before: undefined, after: device }],
    };
  },

  updateDevice(doc: ScenarioDocument, id: string, updates: Partial<ScenarioDevice>): Omit<Command, 'at'> | null {
    const before = doc.devices[id];
    if (!before) return null;
    return {
      label: `Edit ${before.name}`,
      coalesceKey: `update-device-${id}`,
      mutations: [{ kind: 'device', id, before, after: { ...before, ...updates } }],
    };
  },

  moveDevices(doc: ScenarioDocument, moves: { id: string; position: { x: number; y: number } }[]): Omit<Command, 'at'> {
    const mutations: Mutation[] = [];
    for (const { id, position } of moves) {
      const before = doc.devices[id];
      if (!before) continue;
      mutations.push({ kind: 'device', id, before, after: { ...before, position } });
    }
    return {
      label: moves.length > 1 ? `Move ${moves.length} devices` : 'Move device',
      coalesceKey: `move-${moves.map((m) => m.id).sort().join(',')}`,
      mutations,
    };
  },

  /** Delete devices + every flow touching them (the full cascade). */
  deleteDevices(doc: ScenarioDocument, ids: string[]): Omit<Command, 'at'> {
    const idSet = new Set(ids);
    const mutations: Mutation[] = [];
    for (const id of ids) {
      const device = doc.devices[id];
      if (device) mutations.push({ kind: 'device', id, before: device, after: undefined });
    }
    for (const flow of Object.values(doc.flows)) {
      if (idSet.has(flow.sourceDeviceId) || idSet.has(flow.targetDeviceId)) {
        mutations.push({ kind: 'flow', id: flow.id, before: flow, after: undefined });
      }
    }
    for (const zone of Object.values(doc.zones)) {
      const remaining = (zone.deviceIds ?? []).filter((d) => !idSet.has(d));
      if (remaining.length !== (zone.deviceIds ?? []).length) {
        mutations.push({ kind: 'zone', id: zone.id, before: zone, after: { ...zone, deviceIds: remaining } });
      }
    }
    return {
      label: ids.length > 1 ? `Delete ${ids.length} devices` : 'Delete device',
      mutations,
    };
  },

  addFlow(flow: ScenarioFlow): Omit<Command, 'at'> {
    return {
      label: 'Add flow',
      mutations: [{ kind: 'flow', id: flow.id, before: undefined, after: flow }],
    };
  },

  updateFlow(doc: ScenarioDocument, id: string, updates: Partial<ScenarioFlow>): Omit<Command, 'at'> | null {
    const before = doc.flows[id];
    if (!before) return null;
    return {
      label: 'Edit flow',
      coalesceKey: `update-flow-${id}`,
      mutations: [{ kind: 'flow', id, before, after: { ...before, ...updates } }],
    };
  },

  deleteFlows(doc: ScenarioDocument, ids: string[]): Omit<Command, 'at'> {
    const mutations: Mutation[] = [];
    for (const id of ids) {
      const flow = doc.flows[id];
      if (flow) mutations.push({ kind: 'flow', id, before: flow, after: undefined });
    }
    return { label: ids.length > 1 ? `Delete ${ids.length} flows` : 'Delete flow', mutations };
  },

  deleteConduits(doc: ScenarioDocument, ids: string[]): Omit<Command, 'at'> {
    const mutations: Mutation[] = [];
    for (const id of ids) {
      const conduit = doc.conduits[id];
      if (conduit) mutations.push({ kind: 'conduit', id, before: conduit, after: undefined });
    }
    return { label: ids.length > 1 ? `Delete ${ids.length} conduits` : 'Delete conduit', mutations };
  },

  addZone(zone: ScenarioZone): Omit<Command, 'at'> {
    return {
      label: `Add zone ${zone.name}`,
      mutations: [{ kind: 'zone', id: zone.id, before: undefined, after: zone }],
    };
  },

  updateZone(doc: ScenarioDocument, id: string, updates: Partial<ScenarioZone>): Omit<Command, 'at'> | null {
    const before = doc.zones[id];
    if (!before) return null;
    return {
      label: `Edit ${before.name}`,
      coalesceKey: `update-zone-${id}`,
      mutations: [{ kind: 'zone', id, before, after: { ...before, ...updates } }],
    };
  },

  /**
   * Move a zone and shift its member devices' absolute positions by the
   * same delta (members are stored in absolute coordinates).
   */
  moveZone(doc: ScenarioDocument, id: string, position: { x: number; y: number }): Omit<Command, 'at'> | null {
    const zone = doc.zones[id];
    if (!zone) return null;
    const dx = position.x - (zone.position?.x ?? 0);
    const dy = position.y - (zone.position?.y ?? 0);
    const mutations: Mutation[] = [{ kind: 'zone', id, before: zone, after: { ...zone, position } }];
    for (const device of Object.values(doc.devices)) {
      if (device.zoneId !== id) continue;
      mutations.push({
        kind: 'device',
        id: device.id,
        before: device,
        after: {
          ...device,
          position: { x: (device.position?.x ?? 0) + dx, y: (device.position?.y ?? 0) + dy },
        },
      });
    }
    return { label: `Move ${zone.name}`, coalesceKey: `move-zone-${id}`, mutations };
  },

  /** Delete zones: members keep their positions but leave the zone; conduits touching the zone go too. */
  deleteZones(doc: ScenarioDocument, ids: string[]): Omit<Command, 'at'> {
    const idSet = new Set(ids);
    const mutations: Mutation[] = [];
    for (const id of ids) {
      const zone = doc.zones[id];
      if (zone) mutations.push({ kind: 'zone', id, before: zone, after: undefined });
    }
    for (const device of Object.values(doc.devices)) {
      if (device.zoneId && idSet.has(device.zoneId)) {
        mutations.push({ kind: 'device', id: device.id, before: device, after: { ...device, zoneId: undefined } });
      }
    }
    for (const conduit of Object.values(doc.conduits)) {
      if (idSet.has(conduit.sourceZoneId) || idSet.has(conduit.targetZoneId)) {
        mutations.push({ kind: 'conduit', id: conduit.id, before: conduit, after: undefined });
      }
    }
    return { label: ids.length > 1 ? `Delete ${ids.length} zones` : 'Delete zone', mutations };
  },

  /** Change a device's zone membership (drag-in / drag-out). */
  setDeviceZone(
    doc: ScenarioDocument,
    deviceId: string,
    zoneId: string | undefined,
    position: { x: number; y: number },
  ): Omit<Command, 'at'> | null {
    const device = doc.devices[deviceId];
    if (!device) return null;
    const zoneName = zoneId ? doc.zones[zoneId]?.name : undefined;
    return {
      label: zoneName ? `Move ${device.name} into ${zoneName}` : `Move ${device.name} out of zone`,
      mutations: [{ kind: 'device', id: deviceId, before: device, after: { ...device, zoneId, position } }],
    };
  },

  setMeta(doc: ScenarioDocument, updates: Partial<ScenarioMeta>): Omit<Command, 'at'> {
    const before: Partial<ScenarioMeta> = {};
    for (const key of Object.keys(updates) as (keyof ScenarioMeta)[]) {
      (before as Record<string, unknown>)[key] = doc.meta[key];
    }
    return {
      label: 'Edit scenario settings',
      coalesceKey: 'meta',
      mutations: [{ kind: 'meta', before, after: updates }],
    };
  },
};
