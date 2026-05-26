/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Properties panel for cluster-to-cluster aggregate edges.
 *
 * Rendered when the user is in a group-by view (e.g. By Zone) and clicks
 * one of the aggregate edges that connects two cluster nodes. Shows the
 * two endpoints, the protocols that ride between them, and a click-to-
 * focus list of the underlying flows merged into the aggregate.
 */

import React, { useMemo } from 'react';
import { Typography, Tag, Divider, Empty, Tooltip, Button } from 'antd';
import { ArrowRightOutlined } from '@ant-design/icons';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useUIStore } from '../../stores/uiStore';
import type { AggregateEdgeInfo } from '../canvas/edges/FlowEdge';
import type { ProtocolType } from '../../types';
import { PROTOCOL_COLORS, PROTOCOL_LABELS } from '../../constants/protocols';
import { TEXT_BODY, TEXT_MUTED, BG_CODE, BORDER_DEFAULT } from '../../constants/theme';

const { Text } = Typography;

interface Props {
  aggregateInfo: AggregateEdgeInfo;
}

const ClusterDot: React.FC<{ color: string; label: string }> = ({ color, label }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
    <span
      style={{
        width: 10,
        height: 10,
        borderRadius: '50%',
        background: color,
        flexShrink: 0,
      }}
    />
    <Text
      style={{
        color: TEXT_BODY,
        fontWeight: 500,
        fontSize: 13,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}
      title={label}
    >
      {label}
    </Text>
  </div>
);

const ClusterEdgePropertyForm: React.FC<Props> = ({ aggregateInfo }) => {
  const flows = useScenarioStore((state) => state.flows);
  const devices = useScenarioStore((state) => state.devices);
  const setPropertyContext = useUIStore((state) => state.setPropertyContext);
  const setSelection = useUIStore((state) => state.setSelection);
  const setSelectedAggregateEdge = useUIStore((state) => state.setSelectedAggregateEdge);

  // Group the underlying flows by protocol for a compact summary.
  const protocolBreakdown = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const id of aggregateInfo.flowIds) {
      const f = flows[id];
      if (!f) continue;
      counts[f.protocol] = (counts[f.protocol] ?? 0) + 1;
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [aggregateInfo.flowIds, flows]);

  const flowRows = useMemo(() => {
    return aggregateInfo.flowIds
      .map((id) => {
        const f = flows[id];
        if (!f) return null;
        return {
          id,
          name: f.name,
          protocol: f.protocol,
          sourceName: devices[f.sourceDeviceId]?.name ?? f.sourceDeviceId,
          targetName: devices[f.targetDeviceId]?.name ?? f.targetDeviceId,
        };
      })
      .filter((row): row is NonNullable<typeof row> => row !== null);
  }, [aggregateInfo.flowIds, flows, devices]);

  const handleFlowClick = (flowId: string) => {
    setSelectedAggregateEdge(null);
    setPropertyContext('flow', [flowId]);
    setSelection([], [flowId]);
  };

  return (
    <div>
      <Text strong style={{ color: TEXT_BODY, display: 'block', marginBottom: 4 }}>
        Group-to-Group Communications
      </Text>
      <Text style={{ color: TEXT_MUTED, fontSize: 11, display: 'block', marginBottom: 16 }}>
        Aggregate edge from the &quot;{aggregateInfo.groupModeLabel}&quot; group view
      </Text>

      {/* Endpoints */}
      <div
        style={{
          background: BG_CODE,
          border: `1px solid ${BORDER_DEFAULT}`,
          borderRadius: 6,
          padding: 12,
          marginBottom: 16,
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <ClusterDot
            color={aggregateInfo.sourceClusterColor}
            label={aggregateInfo.sourceClusterLabel}
          />
          <ArrowRightOutlined
            style={{
              color: TEXT_MUTED,
              fontSize: 12,
              transform: 'rotate(90deg)',
              marginLeft: 2,
            }}
          />
          <ClusterDot
            color={aggregateInfo.targetClusterColor}
            label={aggregateInfo.targetClusterLabel}
          />
        </div>
      </div>

      {/* Summary stats */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
        <div>
          <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block' }}>Flows</Text>
          <Text style={{ color: TEXT_BODY, fontSize: 18, fontWeight: 600 }}>
            {aggregateInfo.flowIds.length}
          </Text>
        </div>
        <div>
          <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block' }}>Protocols</Text>
          <Text style={{ color: TEXT_BODY, fontSize: 18, fontWeight: 600 }}>
            {aggregateInfo.protocols.length}
          </Text>
        </div>
      </div>

      {/* Protocol breakdown */}
      <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 6 }}>
        Protocols
      </Text>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 16 }}>
        {protocolBreakdown.length > 0 ? (
          protocolBreakdown.map(([proto, count]) => (
            <Tag
              key={proto}
              color={PROTOCOL_COLORS[proto as ProtocolType] ?? '#6a9fd4'}
              style={{ margin: 0 }}
            >
              {PROTOCOL_LABELS[proto] ?? proto.toUpperCase()} × {count}
            </Tag>
          ))
        ) : (
          <Text style={{ color: TEXT_MUTED, fontSize: 12 }}>None</Text>
        )}
      </div>

      <Divider style={{ borderColor: BORDER_DEFAULT, margin: '12px 0' }} />

      {/* Underlying flows list */}
      <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 6 }}>
        Underlying flows ({flowRows.length})
      </Text>
      {flowRows.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Text style={{ color: TEXT_MUTED, fontSize: 12 }}>
              No flows in this aggregate
            </Text>
          }
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {flowRows.map((row) => (
            <Tooltip
              key={row.id}
              title={`${row.sourceName} → ${row.targetName}`}
              placement="left"
            >
              <Button
                type="text"
                size="small"
                onClick={() => handleFlowClick(row.id)}
                style={{
                  background: BG_CODE,
                  border: `1px solid ${BORDER_DEFAULT}`,
                  borderRadius: 4,
                  textAlign: 'left',
                  height: 'auto',
                  padding: '6px 8px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  gap: 2,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    width: '100%',
                    gap: 8,
                  }}
                >
                  <Text
                    style={{
                      color: TEXT_BODY,
                      fontSize: 12,
                      fontWeight: 500,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      flex: 1,
                    }}
                  >
                    {row.name || `${row.sourceName} → ${row.targetName}`}
                  </Text>
                  <Tag
                    color={PROTOCOL_COLORS[row.protocol] ?? '#6a9fd4'}
                    style={{ margin: 0, fontSize: 10 }}
                  >
                    {PROTOCOL_LABELS[row.protocol] ?? row.protocol.toUpperCase()}
                  </Tag>
                </div>
                <Text
                  style={{
                    color: TEXT_MUTED,
                    fontSize: 10,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    width: '100%',
                  }}
                >
                  {row.sourceName} → {row.targetName}
                </Text>
              </Button>
            </Tooltip>
          ))}
        </div>
      )}

      <Divider style={{ borderColor: BORDER_DEFAULT, margin: '16px 0 8px' }} />
      <Text style={{ fontSize: 11, color: TEXT_MUTED }}>
        Click any flow above to edit its individual properties.
      </Text>
    </div>
  );
};

export default ClusterEdgePropertyForm;
