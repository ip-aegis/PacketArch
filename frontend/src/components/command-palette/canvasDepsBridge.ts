/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Canvas deps bridge.
 *
 * The command palette is rendered globally in AppLayout but needs optional
 * canvas deps from the Studio page. The Studio page registers its
 * ReactFlow-dependent callbacks via this module-level ref, which the palette
 * reads. This avoids lifting ReactFlowProvider to AppLayout.
 */
import type { CanvasDeps } from './useCommands';

let _canvasDeps: CanvasDeps | null = null;

export function registerCanvasDeps(deps: CanvasDeps | null): void {
  _canvasDeps = deps;
}

export function getCanvasDeps(): CanvasDeps | null {
  return _canvasDeps;
}
