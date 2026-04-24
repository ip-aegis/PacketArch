/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * EULA / license acknowledgment API.
 */

import apiClient from './client';

export interface AcknowledgmentStatus {
  document: string;
  current_version: string;
  accepted: boolean;
  accepted_version: string | null;
  accepted_at: string | null;
}

export interface AcknowledgmentAccept {
  document: string;
  version: string;
}

const PREFIX = '/api/v1/acknowledgments';

export const acknowledgmentsApi = {
  async getStatus(): Promise<AcknowledgmentStatus> {
    const response = await apiClient.get<AcknowledgmentStatus>(`${PREFIX}/status`);
    return response.data;
  },

  async accept(payload: AcknowledgmentAccept): Promise<void> {
    await apiClient.post(PREFIX, payload);
  },
};

export default acknowledgmentsApi;
