/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Traffic Agents Store
 * Zustand store for managing remote traffic agents
 */

import { create } from 'zustand';
import { agentsApi } from '../api/agents';
import { extractErrorMessage } from '../utils/errorUtils';
import { createResourceSlice } from './createResourceStore';
import type {
  TrafficAgent,
  TrafficAgentWithToken,
  AgentCreate,
  AgentUpdate,
  AgentConnectionInfo,
  AgentInterface,
  AgentDeployment,
  DeploymentCreate,
} from '../types/agent';

const crud = createResourceSlice<TrafficAgent, AgentCreate, AgentUpdate>({
  resourceName: 'agent',
  api: agentsApi,
  listExtractor: (r) => r.agents,
  itemsKey: 'agents',
  selectedKey: 'selectedAgent',
});

interface AgentsState {
  // Data
  agents: TrafficAgent[];
  selectedAgent: TrafficAgent | null;
  connectionInfo: AgentConnectionInfo | null;
  interfaces: AgentInterface[];
  deployments: AgentDeployment[];
  connectedAgents: AgentConnectionInfo[];
  standardVersion: string | null;

  // Loading states
  isLoading: boolean;
  isLoadingConnection: boolean;
  isLoadingInterfaces: boolean;
  isLoadingDeployments: boolean;

  // Error state
  error: string | null;

  // Pagination
  total: number;
  page: number;
  pageSize: number;

  // Actions
  fetchAgents: (page?: number, statusFilter?: string) => Promise<void>;
  fetchAgent: (id: string) => Promise<TrafficAgent>;
  createAgent: (data: AgentCreate) => Promise<TrafficAgentWithToken>;
  updateAgent: (id: string, data: AgentUpdate) => Promise<TrafficAgent>;
  deleteAgent: (id: string) => Promise<void>;
  regenerateToken: (id: string) => Promise<TrafficAgentWithToken>;
  fetchConnection: (id: string) => Promise<AgentConnectionInfo | null>;
  fetchInterfaces: (id: string) => Promise<AgentInterface[]>;
  fetchDeployments: (id: string, activeOnly?: boolean) => Promise<AgentDeployment[]>;
  fetchConnectedAgents: () => Promise<void>;
  deployScenario: (agentId: string, data: DeploymentCreate) => Promise<AgentDeployment>;
  stopDeployment: (agentId: string, scenarioId: string) => Promise<void>;
  setSelectedAgent: (agent: TrafficAgent | null) => void;
  clearError: () => void;
  clearConnectionInfo: () => void;
}

export const useAgentsStore = create<AgentsState>()((set, get) => {
  const { fetchOne, updateOne, deleteOne, clearError } = crud(set, get);

  return {
    // Initial state
    agents: [],
    selectedAgent: null,
    connectionInfo: null,
    interfaces: [],
    deployments: [],
    connectedAgents: [],
    standardVersion: null,
    isLoading: false,
    isLoadingConnection: false,
    isLoadingInterfaces: false,
    isLoadingDeployments: false,
    error: null,
    total: 0,
    page: 1,
    pageSize: 50,

    // fetchAgents is custom — extracts pagination + standardVersion from response
    fetchAgents: async (page = 1, statusFilter?: string) => {
      set({ isLoading: true, error: null });
      try {
        const response = await agentsApi.list(page, get().pageSize, statusFilter);
        set({
          agents: response.agents,
          total: response.total,
          page: response.page,
          standardVersion: response.standard_version,
          isLoading: false,
        });
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to fetch agents');
        set({ error: message, isLoading: false });
        throw error;
      }
    },

    fetchAgent: fetchOne,
    updateAgent: updateOne,

    deleteAgent: async (id: string) => {
      await deleteOne(id);
      set((state) => ({ total: state.total - 1 }));
    },

    clearError,

    // createAgent is custom — returns TrafficAgentWithToken and increments total
    createAgent: async (data: AgentCreate) => {
      set({ isLoading: true, error: null });
      try {
        const agentWithToken = await agentsApi.create(data);
        set((state) => ({
          agents: [...state.agents, agentWithToken],
          total: state.total + 1,
          isLoading: false,
        }));
        return agentWithToken;
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to create agent');
        set({ error: message, isLoading: false });
        throw error;
      }
    },

    regenerateToken: async (id: string) => {
      set({ isLoading: true, error: null });
      try {
        const agentWithToken = await agentsApi.regenerateToken(id);
        set((state) => ({
          agents: state.agents.map((a) => (a.id === id ? agentWithToken : a)),
          selectedAgent: state.selectedAgent?.id === id ? agentWithToken : state.selectedAgent,
          isLoading: false,
        }));
        return agentWithToken;
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to regenerate token');
        set({ error: message, isLoading: false });
        throw error;
      }
    },

    fetchConnection: async (id: string) => {
      set({ isLoadingConnection: true });
      try {
        const info = await agentsApi.getConnection(id);
        set({ connectionInfo: info, isLoadingConnection: false });
        return info;
      } catch {
        set({ connectionInfo: null, isLoadingConnection: false });
        return null;
      }
    },

    fetchInterfaces: async (id: string) => {
      set({ isLoadingInterfaces: true });
      try {
        const response = await agentsApi.getInterfaces(id);
        set({ interfaces: response.interfaces, isLoadingInterfaces: false });
        return response.interfaces;
      } catch (error: unknown) {
        set({ interfaces: [], isLoadingInterfaces: false });
        throw error;
      }
    },

    fetchDeployments: async (id: string, activeOnly = true) => {
      set({ isLoadingDeployments: true });
      try {
        const deployments = await agentsApi.listDeployments(id, activeOnly);
        set({ deployments, isLoadingDeployments: false });
        return deployments;
      } catch (error: unknown) {
        set({ deployments: [], isLoadingDeployments: false });
        throw error;
      }
    },

    fetchConnectedAgents: async () => {
      try {
        const connected = await agentsApi.listConnected();
        set({ connectedAgents: connected });
      } catch {
        set({ connectedAgents: [] });
      }
    },

    deployScenario: async (agentId: string, data: DeploymentCreate) => {
      set({ isLoading: true, error: null });
      try {
        const deployment = await agentsApi.deploy(agentId, data);
        set((state) => ({
          deployments: [...state.deployments, deployment],
          isLoading: false,
        }));
        return deployment;
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to deploy scenario');
        set({ error: message, isLoading: false });
        throw error;
      }
    },

    stopDeployment: async (agentId: string, scenarioId: string) => {
      set({ isLoading: true, error: null });
      try {
        await agentsApi.stopDeployment(agentId, scenarioId);
        set((state) => ({
          deployments: state.deployments.filter((d) => d.scenario_id !== scenarioId),
          isLoading: false,
        }));
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to stop deployment');
        set({ error: message, isLoading: false });
        throw error;
      }
    },

    setSelectedAgent: (agent: TrafficAgent | null) => {
      set({ selectedAgent: agent, connectionInfo: null, interfaces: [], deployments: [] });
    },

    clearConnectionInfo: () => {
      set({ connectionInfo: null, interfaces: [], deployments: [] });
    },
  };
});

export default useAgentsStore;
