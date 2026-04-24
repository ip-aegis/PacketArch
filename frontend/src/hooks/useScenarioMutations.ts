/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Custom hooks for scenario CRUD mutations.
 *
 * Encapsulates create, duplicate, delete, bulk-delete, import,
 * create-from-template, and update mutations so they can be shared
 * between ScenariosPage and any other component that needs them.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';
import {
  scenariosApi,
  type ScenarioCreate,
  type ScenarioSummary,
} from '../api/scenarios';
import {
  templatesApi,
  type CreateFromTemplateRequest,
} from '../api/templates';
import { extractErrorMessage } from '../utils/errorUtils';

export interface ImportedScenarioData {
  name: string;
  definition: Record<string, unknown>;
  vertical?: string;
  description?: string;
}

export interface ForceDeleteModalState {
  visible: boolean;
  scenarioId: string | null;
  scenarioName: string;
  activeAgentDeployments: number;
  activeDockerDeployments: number;
}

const INITIAL_FORCE_DELETE: ForceDeleteModalState = {
  visible: false,
  scenarioId: null,
  scenarioName: '',
  activeAgentDeployments: 0,
  activeDockerDeployments: 0,
};

export interface UseScenarioMutationsOptions {
  /** Called after template-create modal should close */
  onTemplateCreated?: () => void;
  /** Called after create modal should close */
  onCreated?: () => void;
  /** Called after import modal should close */
  onImported?: () => void;
  /** Current page items (used to resolve scenario names on force-delete) */
  scenarioItems?: ScenarioSummary[];
}

export function useScenarioMutations(options: UseScenarioMutationsOptions = {}) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { modal, message } = App.useApp();

  const [forceDeleteModal, setForceDeleteModal] =
    useState<ForceDeleteModalState>(INITIAL_FORCE_DELETE);

  // ── Create ─────────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: (data: ScenarioCreate) => scenariosApi.create(data),
    onSuccess: (scenario) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      message.success('Scenario created successfully');
      options.onCreated?.();
      navigate(`/studio?scenario=${scenario.id}`);
    },
    onError: (error: unknown) => {
      message.error(
        `Failed to create scenario: ${extractErrorMessage(error, 'Unknown error')}`,
      );
    },
  });

  // ── Duplicate ──────────────────────────────────────────────────────
  const duplicateMutation = useMutation({
    mutationFn: (id: string) => scenariosApi.duplicate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      message.success('Scenario duplicated successfully');
    },
    onError: (error: unknown) => {
      message.error(
        `Failed to duplicate scenario: ${extractErrorMessage(error, 'Unknown error')}`,
      );
    },
  });

  // ── Delete (with force-delete handling) ────────────────────────────
  const deleteMutation = useMutation({
    mutationFn: ({ id, force }: { id: string; force?: boolean }) =>
      scenariosApi.delete(id, force),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      message.success('Scenario deleted successfully');
      setForceDeleteModal(INITIAL_FORCE_DELETE);
    },
    onError: (error: unknown, variables) => {
      const axiosErr = error as {
        response?: {
          status?: number;
          data?: { detail?: Record<string, unknown> | string };
        };
      };
      const detail = axiosErr.response?.data?.detail;
      const status = axiosErr.response?.status;

      if (
        status === 409 &&
        typeof detail === 'object' &&
        detail !== null &&
        'active_agent_deployments' in detail
      ) {
        const scenario = options.scenarioItems?.find(
          (s) => s.id === variables.id,
        );
        setForceDeleteModal({
          visible: true,
          scenarioId: variables.id,
          scenarioName: scenario?.name || 'Unknown',
          activeAgentDeployments:
            (detail.active_agent_deployments as number) || 0,
          activeDockerDeployments:
            (detail.active_docker_deployments as number) || 0,
        });
        return;
      }

      message.error(
        `Failed to delete scenario: ${extractErrorMessage(error, 'Unknown error')}`,
      );
    },
  });

  // ── Bulk Delete ────────────────────────────────────────────────────
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) => scenariosApi.bulkDelete(ids),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      message.success(result.message);
    },
    onError: (error: unknown) => {
      message.error(
        `Failed to delete scenarios: ${extractErrorMessage(error, 'Unknown error')}`,
      );
    },
  });

  // ── Create from Template ───────────────────────────────────────────
  const createFromTemplateMutation = useMutation({
    mutationFn: (data: CreateFromTemplateRequest) =>
      templatesApi.createFromTemplate(data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      const enhancements: string[] = [];
      if (result.ai_naming_applied) {
        enhancements.push('AI-generated device names');
      }
      const enhancementInfo =
        enhancements.length > 0
          ? ` (enhanced with ${enhancements.join(' and ')})`
          : '';
      message.success(
        `Scenario created with ${result.device_count} devices and ${result.flow_count} flows${enhancementInfo}`,
      );
      options.onTemplateCreated?.();
      navigate(`/studio?scenario=${result.scenario_id}`);
    },
    onError: (error: unknown) => {
      message.error(
        `Failed to create scenario from template: ${extractErrorMessage(error, 'Unknown error')}`,
      );
    },
  });

  // ── Import ─────────────────────────────────────────────────────────
  const importMutation = useMutation({
    mutationFn: (data: ImportedScenarioData) =>
      scenariosApi.import(data as Record<string, unknown>),
    onSuccess: (scenario) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      message.success('Scenario imported successfully');
      options.onImported?.();
      navigate(`/studio?scenario=${scenario.id}`);
    },
    onError: (error: unknown) => {
      message.error(
        `Failed to import scenario: ${extractErrorMessage(error, 'Unknown error')}`,
      );
    },
  });

  // ── Update (description) ───────────────────────────────────────────
  const updateMutation = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: { description: string };
    }) => scenariosApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
    },
    onError: (error: unknown) => {
      message.error(
        `Failed to update scenario: ${extractErrorMessage(error, 'Unknown error')}`,
      );
    },
  });

  // ── Confirm helpers ────────────────────────────────────────────────
  const confirmDelete = (scenario: ScenarioSummary) => {
    modal.confirm({
      title: 'Delete Scenario',
      content: `Are you sure you want to delete "${scenario.name}"? This action cannot be undone.`,
      okText: 'Delete',
      okType: 'danger',
      centered: true,
      onOk: () => deleteMutation.mutateAsync({ id: scenario.id }),
    });
  };

  const confirmBulkDelete = (ids: Set<string>) => {
    modal.confirm({
      title: 'Delete Selected Scenarios',
      content: `Are you sure you want to delete ${ids.size} scenario(s)? This action cannot be undone.`,
      okText: 'Delete All',
      okType: 'danger',
      centered: true,
      onOk: () => bulkDeleteMutation.mutateAsync(Array.from(ids)),
    });
  };

  const resetForceDeleteModal = () =>
    setForceDeleteModal(INITIAL_FORCE_DELETE);

  return {
    // Mutations
    createMutation,
    duplicateMutation,
    deleteMutation,
    bulkDeleteMutation,
    createFromTemplateMutation,
    importMutation,
    updateMutation,

    // Force delete modal state
    forceDeleteModal,
    setForceDeleteModal,
    resetForceDeleteModal,

    // Confirm helpers
    confirmDelete,
    confirmBulkDelete,
  };
}
