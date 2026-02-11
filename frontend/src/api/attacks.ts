/**
 * Attack Simulation API Client
 * Manages attack playbook library and runtime controls.
 */

import apiClient from './client';
import type { AttackPlaybook, AttackPlaybookSummary, AttackState } from '../types/attackPlaybook';

const PREFIX = '/api/v1/attacks';

export const attacksApi = {
  async listPlaybooks(): Promise<AttackPlaybookSummary[]> {
    const response = await apiClient.get<AttackPlaybookSummary[]>(`${PREFIX}/playbooks`);
    return response.data;
  },

  async getPlaybook(playbookId: string): Promise<AttackPlaybook> {
    const response = await apiClient.get<AttackPlaybook>(`${PREFIX}/playbooks/${playbookId}`);
    return response.data;
  },

  async getCompatible(scenarioId: string): Promise<AttackPlaybookSummary[]> {
    const response = await apiClient.get<AttackPlaybookSummary[]>(
      `${PREFIX}/playbooks/compatible/${scenarioId}`
    );
    return response.data;
  },

  async injectAttack(
    scenarioId: string,
    playbookId: string,
    config?: { auto_advance?: boolean; start_mode?: string; intensity?: number },
  ): Promise<void> {
    await apiClient.post(`${PREFIX}/${scenarioId}/inject`, {
      playbook_id: playbookId,
      auto_advance: config?.auto_advance ?? true,
      start_mode: config?.start_mode ?? 'manual',
      intensity: config?.intensity ?? 1.0,
    });
  },

  async startAttack(scenarioId: string, playbookId: string): Promise<void> {
    await apiClient.post(`${PREFIX}/${scenarioId}/start`, { playbook_id: playbookId });
  },

  async stopAttack(scenarioId: string): Promise<void> {
    await apiClient.post(`${PREFIX}/${scenarioId}/stop`);
  },

  async advanceStage(scenarioId: string): Promise<void> {
    await apiClient.post(`${PREFIX}/${scenarioId}/advance`);
  },

  async pauseAttack(scenarioId: string, paused: boolean): Promise<void> {
    await apiClient.post(`${PREFIX}/${scenarioId}/pause`, { paused });
  },

  async getAttackState(scenarioId: string): Promise<AttackState> {
    const response = await apiClient.get<AttackState>(`${PREFIX}/${scenarioId}/state`);
    return response.data;
  },

  async getInjectionStatus(scenarioId: string): Promise<{
    status: 'pending' | 'confirmed' | 'failed';
    message?: string;
    attack?: AttackState;
  }> {
    const response = await apiClient.get(`${PREFIX}/${scenarioId}/injection-status`);
    return response.data;
  },
};
