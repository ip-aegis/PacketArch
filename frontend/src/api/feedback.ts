/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import apiClient from './client';

export interface FeedbackPayload {
  name: string;
  email: string;
  message: string;
}

export const feedbackApi = {
  async submit(payload: FeedbackPayload): Promise<void> {
    await apiClient.post('/api/v1/feedback', payload);
  },
};
