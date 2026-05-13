/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Per-scenario Purdue-aware cell isolation toggle.
 *
 * The dropdown writes the chosen mode into scenarioStore.cellIsolation,
 * which the auto-save plumbing flushes into definition.cell_isolation.
 * Switching to strict_northbound is destructive (prunes cell↔cell flows
 * and conduits), so it goes through a confirmation modal that previews
 * exactly what will be removed.
 */

import React, { useEffect, useState } from 'react';
import {
  App,
  Button,
  Modal,
  Select,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import { LockOutlined } from '@ant-design/icons';
import { useScenarioStore } from '../../stores/scenarioStore';
import {
  scenariosApi,
  type CellIsolationPreviewResponse,
} from '../../api/scenarios';
import { extractErrorMessage } from '../../utils/errorUtils';
import type { CellIsolationMode } from '../../types';

const { Text } = Typography;

const MODE_OPTIONS: Array<{ value: CellIsolationMode; label: string; description: string }> = [
  {
    value: 'off',
    label: 'Off — permissive',
    description: 'Conduit checks are advisory. East/west cell traffic is allowed.',
  },
  {
    value: 'conduit_gated',
    label: 'Conduit-gated',
    description:
      'Cross-cell flows (L0–L2 ↔ L0–L2) are dropped at runtime unless an explicit conduit permits the protocol.',
  },
  {
    value: 'strict_northbound',
    label: 'Strict — northbound only',
    description:
      'Cells are hermetic. No cell↔cell traffic ever. Cells may only talk to L3+ zones. Cell-to-cell conduits are pruned.',
  },
];

interface Props {
  scenarioId: string | null;
  buttonStyle: React.CSSProperties;
}

const CellIsolationControl: React.FC<Props> = ({ scenarioId, buttonStyle }) => {
  const { message } = App.useApp();
  const cellIsolation = useScenarioStore((s) => s.cellIsolation);
  const setCellIsolation = useScenarioStore((s) => s.setCellIsolation);

  const [pendingMode, setPendingMode] = useState<CellIsolationMode | null>(null);
  const [preview, setPreview] = useState<CellIsolationPreviewResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [applying, setApplying] = useState(false);

  const currentMode = cellIsolation?.mode ?? 'off';

  useEffect(() => {
    if (pendingMode !== 'strict_northbound' || !scenarioId) return;
    setLoadingPreview(true);
    scenariosApi
      .previewCellIsolationStrict(scenarioId)
      .then(setPreview)
      .catch((err) => {
        message.error(`Failed to preview prune: ${extractErrorMessage(err, 'Unknown error')}`);
        setPendingMode(null);
      })
      .finally(() => setLoadingPreview(false));
  }, [pendingMode, scenarioId, message]);

  const handleSelect = (value: CellIsolationMode) => {
    if (value === currentMode) return;
    if (value === 'strict_northbound') {
      // Destructive — require explicit confirmation + preview.
      setPendingMode(value);
      return;
    }
    // Non-destructive transitions write straight through.
    setCellIsolation({
      mode: value,
      applies_to_levels: cellIsolation?.applies_to_levels ?? [0, 1, 2],
    });
  };

  const cancelStrict = () => {
    setPendingMode(null);
    setPreview(null);
  };

  const confirmStrict = async () => {
    if (!scenarioId) {
      // No saved scenario yet — just flip the local mode.
      setCellIsolation({
        mode: 'strict_northbound',
        applies_to_levels: cellIsolation?.applies_to_levels ?? [0, 1, 2],
      });
      cancelStrict();
      return;
    }
    setApplying(true);
    try {
      const result = await scenariosApi.applyCellIsolationStrict(scenarioId);
      setCellIsolation({
        mode: 'strict_northbound',
        applies_to_levels: cellIsolation?.applies_to_levels ?? [0, 1, 2],
      });
      // Mutate store flow + conduit maps to mirror what the backend just did,
      // so the canvas reflects the prune without a refetch.
      const store = useScenarioStore.getState();
      const removedFlows = new Set(result.removed_flow_ids);
      const removedConduits = new Set(result.removed_conduit_ids);
      const newFlows = Object.fromEntries(
        Object.entries(store.flows).filter(([fid]) => !removedFlows.has(fid)),
      );
      const newConduits = Object.fromEntries(
        Object.entries(store.conduits).filter(([cid]) => !removedConduits.has(cid)),
      );
      useScenarioStore.setState({
        flows: newFlows,
        conduits: newConduits,
        isDirty: false,
      });
      message.success(
        `Strict cell isolation applied. Removed ${result.removed_flow_ids.length} cross-cell flow(s) and ${result.removed_conduit_ids.length} conduit(s). A version snapshot was created.`,
      );
      cancelStrict();
    } catch (err) {
      message.error(
        `Failed to apply strict isolation: ${extractErrorMessage(err, 'Unknown error')}`,
      );
    } finally {
      setApplying(false);
    }
  };

  const tooltipTitle = `Cell Isolation: ${MODE_OPTIONS.find((o) => o.value === currentMode)?.label}`;

  return (
    <>
      <Tooltip title={tooltipTitle}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          <LockOutlined style={{ ...buttonStyle, padding: 4 }} />
          <Select<CellIsolationMode>
            value={currentMode}
            onChange={handleSelect}
            size="small"
            style={{ minWidth: 160 }}
            options={MODE_OPTIONS.map((o) => ({
              value: o.value,
              label: (
                <Tooltip title={o.description} placement="right">
                  <span>{o.label}</span>
                </Tooltip>
              ),
            }))}
          />
        </div>
      </Tooltip>

      <Modal
        open={pendingMode === 'strict_northbound'}
        title="Switch to strict cell isolation?"
        onCancel={cancelStrict}
        onOk={confirmStrict}
        okText="Apply strict isolation"
        okType="danger"
        confirmLoading={applying}
        width={640}
        centered
      >
        <Text>
          Strict mode hermetically isolates Purdue Level 0–2 cells. Cell↔cell
          flows are dropped at runtime; cell-to-cell conduits become noise and
          will be pruned now. A version snapshot is created first so you can
          roll back from the History drawer.
        </Text>

        {loadingPreview && (
          <div style={{ marginTop: 16 }}>Loading preview…</div>
        )}

        {!loadingPreview && preview && (
          <div style={{ marginTop: 16 }}>
            <Text strong>Flows to remove ({preview.flows.length})</Text>
            {preview.flows.length === 0 ? (
              <div style={{ color: '#8c8c8c', marginBottom: 8 }}>
                No cell-to-cell flows present.
              </div>
            ) : (
              <ul style={{ marginTop: 4, marginBottom: 12, paddingLeft: 18 }}>
                {preview.flows.slice(0, 25).map((f) => (
                  <li key={f.id}>
                    <Tag>{f.protocol || 'unknown'}</Tag>
                    {f.name}{' '}
                    <Text type="secondary">
                      ({f.source_zone} → {f.target_zone})
                    </Text>
                  </li>
                ))}
                {preview.flows.length > 25 && (
                  <li>…and {preview.flows.length - 25} more.</li>
                )}
              </ul>
            )}

            <Text strong>Conduits to remove ({preview.conduits.length})</Text>
            {preview.conduits.length === 0 ? (
              <div style={{ color: '#8c8c8c' }}>
                No cell-to-cell conduits present.
              </div>
            ) : (
              <ul style={{ marginTop: 4, paddingLeft: 18 }}>
                {preview.conduits.slice(0, 25).map((c) => (
                  <li key={c.id}>
                    {c.name}{' '}
                    <Text type="secondary">
                      ({c.source_zone} ↔ {c.target_zone}
                      {c.allowed_protocols?.length
                        ? ` · ${c.allowed_protocols.join(', ')}`
                        : ''}
                      )
                    </Text>
                  </li>
                ))}
                {preview.conduits.length > 25 && (
                  <li>…and {preview.conduits.length - 25} more.</li>
                )}
              </ul>
            )}
          </div>
        )}
      </Modal>
    </>
  );
};

export default CellIsolationControl;
