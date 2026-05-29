/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * BulkAgentUpdateModal — live progress for an "Update All" operation.
 *
 * After the banner triggers updates on N agents, this modal polls the
 * bulk update-status endpoint every 2s and shows each agent's live stage
 * (downloading %, loading, restarting) and final outcome (success, or
 * failure with the agent's error, e.g. "Docker not available"). Closes
 * cleanly once every tracked agent reaches a terminal state.
 */

import React, { useEffect, useRef, useState } from 'react';
import { Button, List, Modal, Progress, Space, Tag, Typography } from 'antd';
import {
  CheckCircleTwoTone,
  CloseCircleTwoTone,
  CloudUploadOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { agentsApi } from '../../api/agents';
import type { AgentUpdateStatus } from '../../types/agent';

const { Text } = Typography;

const TERMINAL = ['complete', 'failed', 'timeout', 'error'];

const STAGE_LABEL: Record<string, string> = {
  idle: 'Queued',
  initiated: 'Initiating',
  downloading: 'Downloading',
  loading: 'Loading image',
  restarting: 'Restarting',
  complete: 'Updated',
  failed: 'Failed',
  timeout: 'Timed out',
  error: 'Failed',
};

export interface BulkUpdateTarget {
  id: string;
  name: string;
}

export interface BulkAgentUpdateModalProps {
  open: boolean;
  targets: BulkUpdateTarget[];
  targetVersion?: string | null;
  onClose: () => void;
}

const statusTag = (status: string, progress: number | null) => {
  if (status === 'complete') {
    return <Tag icon={<CheckCircleTwoTone twoToneColor="#52c41a" />} color="success">Updated</Tag>;
  }
  if (['failed', 'timeout', 'error'].includes(status)) {
    return <Tag icon={<CloseCircleTwoTone twoToneColor="#ff4d4f" />} color="error">{STAGE_LABEL[status] ?? 'Failed'}</Tag>;
  }
  const label = STAGE_LABEL[status] ?? status;
  return (
    <Tag icon={<LoadingOutlined />} color="processing">
      {label}{status === 'downloading' && progress != null ? ` ${progress}%` : ''}
    </Tag>
  );
};

const BulkAgentUpdateModal: React.FC<BulkAgentUpdateModalProps> = ({
  open,
  targets,
  targetVersion,
  onClose,
}) => {
  const [statuses, setStatuses] = useState<Record<string, AgentUpdateStatus>>({});
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const targetIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    targetIds.current = new Set(targets.map((t) => t.id));
  }, [targets]);

  useEffect(() => {
    if (!open) {
      if (timer.current) clearInterval(timer.current);
      timer.current = null;
      setStatuses({});
      return;
    }

    const poll = async () => {
      try {
        const all = await agentsApi.getActiveUpdateStatuses();
        const next: Record<string, AgentUpdateStatus> = {};
        for (const s of all) {
          if (targetIds.current.has(s.agent_id)) next[s.agent_id] = s;
        }
        setStatuses(next);
        // Stop polling once every target has reached a terminal state.
        const done =
          targetIds.current.size > 0 &&
          [...targetIds.current].every((id) => next[id] && TERMINAL.includes(next[id].status));
        if (done && timer.current) {
          clearInterval(timer.current);
          timer.current = null;
        }
      } catch {
        /* transient — keep polling */
      }
    };

    void poll();
    timer.current = setInterval(poll, 2000);
    return () => {
      if (timer.current) clearInterval(timer.current);
      timer.current = null;
    };
  }, [open]);

  const list = targets.map((t) => ({ target: t, status: statuses[t.id] }));
  const done = list.filter((r) => r.status && TERMINAL.includes(r.status.status));
  const succeeded = done.filter((r) => r.status!.status === 'complete').length;
  const failed = done.length - succeeded;
  const allDone = targets.length > 0 && done.length === targets.length;

  return (
    <Modal
      title={<Space><CloudUploadOutlined />Updating {targets.length} agent{targets.length !== 1 ? 's' : ''}{targetVersion ? ` to v${targetVersion}` : ''}</Space>}
      open={open}
      onCancel={onClose}
      maskClosable={false}
      width={560}
      footer={
        allDone ? (
          <Button type="primary" onClick={onClose}>Close</Button>
        ) : (
          <Text type="secondary">
            {done.length}/{targets.length} finished — please wait…
          </Text>
        )
      }
    >
      <div style={{ marginBottom: 12 }}>
        <Space size="middle">
          <Text>{done.length}/{targets.length} finished</Text>
          {succeeded > 0 && <Text type="success">{succeeded} updated</Text>}
          {failed > 0 && <Text type="danger">{failed} failed</Text>}
        </Space>
      </div>
      <List
        size="small"
        dataSource={list}
        rowKey={(r) => r.target.id}
        renderItem={(r) => {
          const s = r.status;
          const status = s?.status ?? 'idle';
          const isFail = ['failed', 'timeout', 'error'].includes(status);
          return (
            <List.Item>
              <div style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                  <Text strong ellipsis style={{ maxWidth: 240 }}>{r.target.name}</Text>
                  {statusTag(status, s?.progress ?? null)}
                </div>
                {status === 'downloading' && s?.progress != null && (
                  <Progress percent={s.progress} size="small" status="active" style={{ marginTop: 4 }} />
                )}
                {(s?.message || s?.error) && (
                  <Text type={isFail ? 'danger' : 'secondary'} style={{ fontSize: 12 }}>
                    {isFail ? (s?.error || s?.message) : s?.message}
                  </Text>
                )}
              </div>
            </List.Item>
          );
        }}
      />
    </Modal>
  );
};

export default BulkAgentUpdateModal;
