/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Rationality badge for the canvas toolbar (Phase 7).
 *
 * Shows the fraction of flows that are "on the architecture rail"
 * (i.e. endorsed by the typed comm matrix). Click for a breakdown
 * popover listing off-rail and protocol-mismatched flows.
 */

import React, { useMemo } from 'react';
import { Badge, Button, Empty, Popover, Space, Tag, Tooltip, Typography } from 'antd';
import { SafetyCertificateOutlined } from '@ant-design/icons';
import { useUIStore } from '../../stores/uiStore';
import { useScenarioStore } from '../../stores/scenarioStore';
import {
  useRationalityStore,
  useRationalitySummary,
  type FlowRationality,
} from '../../stores/rationalityStore';

const { Text } = Typography;

const STATUS_LABEL: Record<FlowRationality['status'], string> = {
  ok: 'On the rail',
  mismatch: 'Protocol mismatch',
  'off-rail': 'Off the rail',
  unknown: 'Unknown role',
};

const STATUS_COLOR: Record<FlowRationality['status'], string> = {
  ok: 'success',
  mismatch: 'warning',
  'off-rail': 'orange',
  unknown: 'default',
};

const RationalityBadge: React.FC = () => {
  const summary = useRationalitySummary();
  const results = useRationalityStore((s) => s.results);
  const flows = useScenarioStore((s) => s.flows);
  const devices = useScenarioStore((s) => s.devices);
  const setSelection = useUIStore((s) => s.setSelection);
  const setPropertyContext = useUIStore((s) => s.setPropertyContext);

  const offRail = useMemo(
    () =>
      Object.values(results).filter(
        (r) => r.status === 'off-rail' || r.status === 'mismatch',
      ),
    [results],
  );

  const score = summary.score;
  const tone =
    score === 100 ? '#5fb878' : score >= 80 ? '#ffd54a' : '#ff9f4a';

  const popoverContent = (
    <div style={{ width: 360, maxHeight: 420, overflowY: 'auto' }}>
      <Text strong>Architecture rationality</Text>
      <div style={{ marginTop: 8, marginBottom: 12 }}>
        <Space wrap size={[4, 4]}>
          <Tag color="success">{summary.ok} on the rail</Tag>
          {summary.mismatch > 0 && (
            <Tag color="warning">{summary.mismatch} protocol mismatch</Tag>
          )}
          {summary.offRail > 0 && (
            <Tag color="orange">{summary.offRail} off the rail</Tag>
          )}
          {summary.unknown > 0 && (
            <Tag>{summary.unknown} unknown role</Tag>
          )}
        </Space>
      </div>

      {offRail.length === 0 ? (
        <Empty
          description="Every flow is endorsed by the architecture matrix."
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Click a flow to inspect / adjust:
          </Text>
          <div style={{ marginTop: 8 }}>
            {offRail.slice(0, 12).map((r) => {
              const flow = flows[r.flowId];
              if (!flow) return null;
              const src = devices[flow.sourceDeviceId];
              const tgt = devices[flow.targetDeviceId];
              const label = `${src?.name || '?'} → ${tgt?.name || '?'}`;
              return (
                <div
                  key={r.flowId}
                  style={{
                    padding: '6px 8px',
                    borderRadius: 4,
                    background: '#1a2333',
                    border: '1px solid #2a3a52',
                    marginBottom: 6,
                    cursor: 'pointer',
                  }}
                  onClick={() => {
                    setSelection([], [r.flowId]);
                    setPropertyContext('flow', [r.flowId]);
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <Text
                      style={{
                        fontSize: 12,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        maxWidth: 220,
                      }}
                    >
                      {label}
                    </Text>
                    <Tag color={STATUS_COLOR[r.status]} style={{ marginRight: 0 }}>
                      {STATUS_LABEL[r.status]}
                    </Tag>
                  </div>
                  {r.suggestion && (
                    <Text
                      type="secondary"
                      style={{ fontSize: 11, display: 'block', marginTop: 2 }}
                    >
                      {r.suggestion}
                    </Text>
                  )}
                </div>
              );
            })}
            {offRail.length > 12 && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                + {offRail.length - 12} more not shown
              </Text>
            )}
          </div>
        </>
      )}
    </div>
  );

  if (summary.total === 0) {
    return null;
  }

  return (
    <Popover
      content={popoverContent}
      title={null}
      placement="bottomRight"
      trigger="click"
    >
      <Tooltip
        title="Architecture rationality — fraction of flows endorsed by the comm matrix"
        placement="bottom"
      >
        <Button
          type="text"
          size="small"
          icon={<SafetyCertificateOutlined style={{ color: tone }} />}
          style={{ paddingInline: 8 }}
        >
          <Badge
            count={summary.offRail + summary.mismatch}
            offset={[6, -4]}
            size="small"
            color={summary.offRail > 0 ? 'orange' : 'gold'}
          >
            <span style={{ color: tone, fontWeight: 600 }}>{score}%</span>
          </Badge>
        </Button>
      </Tooltip>
    </Popover>
  );
};

export default RationalityBadge;
