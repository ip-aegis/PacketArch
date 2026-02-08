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
};
