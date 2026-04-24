/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Deployments API functions
 */

import { createCrudApi } from './createCrudApi';
import apiClient from './client';
import type {
  UnifiedDeployment,
  DeploymentListResponse,
  DeploymentStatus,
} from '../types/docker';

const PREFIX = '/api/v1/deployments';

export interface DeploymentFilters {
  scenario_id?: string;
  agent_id?: string;
  status?: DeploymentStatus | string;
}

const crud = createCrudApi<UnifiedDeployment>({ prefix: PREFIX });

export const deploymentsApi = {
  get: crud.get,
  remove: crud.delete,

  async list(filters: DeploymentFilters = {}): Promise<DeploymentListResponse> {
    const response = await apiClient.get<DeploymentListResponse>(PREFIX, {
      params: {
        scenario_id: filters.scenario_id,
        agent_id: filters.agent_id,
        status_filter: filters.status,
      },
    });
    return response.data;
  },
};

export default deploymentsApi;
