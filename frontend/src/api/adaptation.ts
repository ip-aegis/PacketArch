/**
 * Adaptation API Client
 * Manages adaptive traffic controls including deployment phase scheduling.
 */

import apiClient from './client';

const PREFIX = '/api/v1/adaptation';

export interface PhaseScheduleInfo {
  active: boolean;
  phase_id?: string;
  name?: string;
  color?: string;
  rate_multiplier?: number;
  progress_pct?: number;
  elapsed_s?: number;
  remaining_s?: number;
  duration_s?: number;
  cycle_count?: number;
  total_phases?: number;
  phase_index?: number;
  cycling?: boolean;
  paused?: boolean;
  forced?: boolean;
  phases?: {
    phase_id: string;
    name: string;
    color: string;
    duration_s: number;
    rate_multiplier: number;
  }[];
}

export interface AdaptationState {
  enabled: boolean;
  phase_schedule?: PhaseScheduleInfo;
  deployment_phase?: {
    name: string;
    phase_id: string;
    progress_pct: number;
    cycle_count: number;
  };
  [key: string]: unknown;
}

export const adaptationApi = {
  async getState(scenarioId: string): Promise<AdaptationState> {
    const response = await apiClient.get<AdaptationState>(`${PREFIX}/${scenarioId}/state`);
    return response.data;
  },

  async skipPhase(scenarioId: string): Promise<void> {
    await apiClient.post(`${PREFIX}/${scenarioId}/phase/skip`);
  },

  async forcePhase(scenarioId: string, phaseId: string): Promise<void> {
    await apiClient.post(`${PREFIX}/${scenarioId}/phase/force`, { phase_id: phaseId });
  },

  async togglePhasePause(scenarioId: string, paused: boolean): Promise<void> {
    await apiClient.post(`${PREFIX}/${scenarioId}/phase/pause`, { paused });
  },
};
