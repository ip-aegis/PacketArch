/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 layout utilities.
 *
 * - `layoutDocument`: zone-aware grid layout honoring the Purdue convention
 *   (L4 at the top, L0 at the bottom). Applied automatically when a
 *   scenario arrives with no saved positions, and available on demand.
 * - `resolveOverlaps`: minimal-displacement de-overlap for scenarios that
 *   WERE laid out (v1's nodes were smaller, so v1 spacings can collide
 *   with v2 cards). Pushes intersecting nodes apart without redesigning
 *   the user's arrangement.
 *
 * Both return command mutations so the change is one undoable step.
 */

import type { ScenarioDocument, Mutation, Command } from '../document/documentStore';
import type { ScenarioDevice, ScenarioZone } from '../../types';

/** Approximate footprint of a card-tier DeviceNode2, incl. breathing room. */
const BOX_W = 210;
const BOX_H = 60;
const GAP_X = 48;
const GAP_Y = 44;
const ZONE_PAD = 28;
const ZONE_HEADER = 44;
const ZONE_GAP = 70;
const GRID = 20;

const snap = (v: number) => Math.round(v / GRID) * GRID;

// ---------------------------------------------------------------------------
// Zone-aware grid layout (Purdue bands: high levels on top)
// ---------------------------------------------------------------------------

interface ZonePlan {
  zone: ScenarioZone | null; // null = unzoned band
  devices: ScenarioDevice[];
  cols: number;
  rows: number;
  width: number;
  height: number;
}

function planZone(zone: ScenarioZone | null, devices: ScenarioDevice[]): ZonePlan {
  const n = Math.max(devices.length, 1);
  // Aim for a ~1.6 aspect ratio block of devices
  const cols = Math.max(1, Math.round(Math.sqrt(n * 1.6)));
  const rows = Math.ceil(n / cols);
  const width = ZONE_PAD * 2 + cols * BOX_W + (cols - 1) * GAP_X;
  const height = ZONE_HEADER + ZONE_PAD + rows * BOX_H + (rows - 1) * GAP_Y + ZONE_PAD;
  return { zone, devices, cols, rows, width, height };
}

export function layoutDocument(doc: ScenarioDocument): Omit<Command, 'at'> | null {
  const devices = Object.values(doc.devices);
  if (devices.length === 0) return null;

  // Group devices by zone
  const byZone = new Map<string | null, ScenarioDevice[]>();
  for (const d of devices) {
    const key = d.zoneId && doc.zones[d.zoneId] ? d.zoneId : null;
    const list = byZone.get(key) ?? [];
    list.push(d);
    byZone.set(key, list);
  }

  // Zones into Purdue bands, highest level first (L4 top → L0 bottom).
  // Zones without a level land between leveled bands and the unzoned band.
  const zonePlans = [...byZone.entries()]
    .filter(([zoneId]) => zoneId !== null)
    .map(([zoneId, ds]) => planZone(doc.zones[zoneId!], ds));
  // Include empty zones so they don't stack at the origin
  for (const zone of Object.values(doc.zones)) {
    if (!byZone.has(zone.id)) zonePlans.push(planZone(zone, []));
  }
  zonePlans.sort((a, b) => (b.zone?.level ?? -1) - (a.zone?.level ?? -1));

  const bands = new Map<number, ZonePlan[]>();
  for (const plan of zonePlans) {
    const level = plan.zone?.level ?? -1;
    const band = bands.get(level) ?? [];
    band.push(plan);
    bands.set(level, band);
  }
  const orderedLevels = [...bands.keys()].sort((a, b) => b - a);

  const mutations: Mutation[] = [];
  let y = 0;
  const placeDevices = (plan: ZonePlan, originX: number, originY: number) => {
    plan.devices.forEach((device, i) => {
      const col = i % plan.cols;
      const row = Math.floor(i / plan.cols);
      const position = {
        x: snap(originX + col * (BOX_W + GAP_X)),
        y: snap(originY + row * (BOX_H + GAP_Y)),
      };
      mutations.push({ kind: 'device', id: device.id, before: device, after: { ...device, position } });
    });
  };

  for (const level of orderedLevels) {
    const band = bands.get(level)!;
    let x = 0;
    const bandHeight = Math.max(...band.map((p) => p.height));
    for (const plan of band) {
      const zone = plan.zone!;
      const zonePos = { x: snap(x), y: snap(y) };
      const dimensions = { width: plan.width, height: plan.height };
      mutations.push({
        kind: 'zone',
        id: zone.id,
        before: zone,
        after: { ...zone, position: zonePos, dimensions },
      });
      placeDevices(plan, zonePos.x + ZONE_PAD, zonePos.y + ZONE_HEADER + ZONE_PAD);
      x += plan.width + ZONE_GAP;
    }
    y += bandHeight + ZONE_GAP;
  }

  // Unzoned devices: plain grid in a bottom band
  const unzoned = byZone.get(null);
  if (unzoned && unzoned.length > 0) {
    const plan = planZone(null, unzoned);
    placeDevices(plan, ZONE_PAD, y + ZONE_PAD);
  }

  return { label: 'Auto layout', mutations };
}

// ---------------------------------------------------------------------------
// De-overlap: minimal displacement, keeps the user's arrangement
// ---------------------------------------------------------------------------

export function resolveOverlaps(doc: ScenarioDocument): Omit<Command, 'at'> | null {
  const devices = Object.values(doc.devices);
  if (devices.length < 2) return null;

  const boxes = devices.map((d) => ({
    id: d.id,
    x: d.position?.x ?? 0,
    y: d.position?.y ?? 0,
  }));

  const MARGIN_X = 24;
  const MARGIN_Y = 20;
  const needW = BOX_W + MARGIN_X;
  const needH = BOX_H + MARGIN_Y;

  let moved = false;
  for (let iter = 0; iter < 60; iter++) {
    let anyThisPass = false;
    for (let i = 0; i < boxes.length; i++) {
      for (let j = i + 1; j < boxes.length; j++) {
        const a = boxes[i];
        const b = boxes[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const overlapX = needW - Math.abs(dx);
        const overlapY = needH - Math.abs(dy);
        if (overlapX <= 0 || overlapY <= 0) continue;
        anyThisPass = true;
        moved = true;
        // Push apart along the axis of least penetration, half each way
        if (overlapX < overlapY) {
          const push = (overlapX / 2 + 1) * (dx >= 0 ? 1 : -1);
          a.x -= push;
          b.x += push;
        } else {
          const push = (overlapY / 2 + 1) * (dy >= 0 ? 1 : -1);
          a.y -= push;
          b.y += push;
        }
      }
    }
    if (!anyThisPass) break;
  }
  if (!moved) return null;

  const mutations: Mutation[] = [];
  for (const box of boxes) {
    const device = doc.devices[box.id];
    const position = { x: snap(box.x), y: snap(box.y) };
    if (device.position?.x !== position.x || device.position?.y !== position.y) {
      mutations.push({ kind: 'device', id: box.id, before: device, after: { ...device, position } });
    }
  }
  if (mutations.length === 0) return null;
  return { label: 'Tidy layout', mutations };
}

/** True when no device or zone carries a meaningful saved position. */
export function isUnpositioned(doc: ScenarioDocument): boolean {
  const devicePositioned = Object.values(doc.devices).some(
    (d) => d.position && (d.position.x !== 0 || d.position.y !== 0),
  );
  const zonePositioned = Object.values(doc.zones).some(
    (z) => z.position && (z.position.x !== 0 || z.position.y !== 0),
  );
  return !devicePositioned && !zonePositioned;
}
