/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Architecture-rail API client.
 *
 * Surfaces the role catalog, archetypes, comm matrix, and flow checker
 * to the canvas editor (Phase 7 — flow validation hints) and the
 * reference-architecture docs view (Phase 8).
 */

import { apiClient } from './client';

const PREFIX = '/api/v1/architecture';

// ---------- Types ----------

export interface RoleSummary {
  id: string;
  name: string;
  category: string;
  purdue_level: number;
  description: string;
  when_to_include: string;
  primary_device_types: string[];
  vertical_applicability: string[];
  required_protocols: string[];
  optional_protocols: string[];
  typical_partners: string[];
  examples: string[];
}

export interface ArchetypeRoleSlot {
  role_id: string;
  count_by_scale: Record<string, number>;
  optional_at: string[];
}

export interface ArchetypeZone {
  id: string;
  name: string;
  purdue_level: number;
  security_level: string;
  description: string;
  is_external: boolean;
  role_slots: ArchetypeRoleSlot[];
}

export interface ArchetypeConduit {
  id: string;
  name: string;
  source_zone: string;
  target_zone: string;
  direction: string;
  allowed_protocols: string[];
  security_level: string;
  description: string;
}

export interface ArchetypeSummary {
  id: string;
  name: string;
  vertical: string;
  pattern: string;
  description: string;
  default_vendor_profile: string;
  supported_vendor_profiles: string[];
  zones: ArchetypeZone[];
  conduits: ArchetypeConduit[];
  notes: string[];
}

export interface CommMatrixEntrySummary {
  src_role: string;
  tgt_role: string;
  vertical: string;
  pattern: string;
  interval_ms_min: number;
  interval_ms_max: number;
  protocol_options: string[];
  description: string;
}

export interface FlowCheckRequest {
  src_role: string;
  tgt_role: string;
  vertical: string;
  protocol?: string;
}

export interface FlowCheckResponse {
  in_matrix: boolean;
  matrix_entries: CommMatrixEntrySummary[];
  suggestion: string | null;
}

// ---------- API ----------

export const architectureApi = {
  async getVerticals(): Promise<string[]> {
    const { data } = await apiClient.get<string[]>(`${PREFIX}/verticals`);
    return data;
  },

  async getScaleTiers(): Promise<string[]> {
    const { data } = await apiClient.get<string[]>(`${PREFIX}/scale-tiers`);
    return data;
  },

  async getVendorProfiles(): Promise<string[]> {
    const { data } = await apiClient.get<string[]>(`${PREFIX}/vendor-profiles`);
    return data;
  },

  async getRoles(vertical?: string): Promise<RoleSummary[]> {
    const params = vertical ? { vertical } : undefined;
    const { data } = await apiClient.get<RoleSummary[]>(`${PREFIX}/roles`, { params });
    return data;
  },

  async getRoleById(roleId: string): Promise<RoleSummary> {
    const { data } = await apiClient.get<RoleSummary>(`${PREFIX}/roles/${roleId}`);
    return data;
  },

  async getArchetypes(vertical?: string): Promise<ArchetypeSummary[]> {
    const params = vertical ? { vertical } : undefined;
    const { data } = await apiClient.get<ArchetypeSummary[]>(`${PREFIX}/archetypes`, { params });
    return data;
  },

  async getArchetypeById(archetypeId: string): Promise<ArchetypeSummary> {
    const { data } = await apiClient.get<ArchetypeSummary>(
      `${PREFIX}/archetypes/${archetypeId}`,
    );
    return data;
  },

  async getCommMatrix(vertical: string): Promise<CommMatrixEntrySummary[]> {
    const { data } = await apiClient.get<CommMatrixEntrySummary[]>(
      `${PREFIX}/comm-matrix`,
      { params: { vertical } },
    );
    return data;
  },

  /**
   * Phase 7: canvas flow checker. Returns whether a (src_role, tgt_role,
   * vertical [, protocol]) flow is endorsed by the architecture rail's
   * communication matrix. The canvas uses this to surface gentle
   * "this flow isn't in the matrix" hints — does not block authoring.
   */
  async checkFlow(request: FlowCheckRequest): Promise<FlowCheckResponse> {
    const { data } = await apiClient.post<FlowCheckResponse>(
      `${PREFIX}/check-flow`,
      request,
    );
    return data;
  },
};
