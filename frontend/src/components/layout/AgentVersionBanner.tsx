/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Global banner warning when agents are running outdated versions.
 * Rendered between Header and Content in AppLayout.
 */

import React, { useState, useEffect, useRef } from 'react';
import { Alert, Button, Space, App } from 'antd';
import { CloudUploadOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAgentsStore } from '../../stores/agentsStore';
import { agentsApi } from '../../api/agents';
import BulkAgentUpdateModal, { type BulkUpdateTarget } from '../agents/BulkAgentUpdateModal';

const AgentVersionBanner: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [dismissed, setDismissed] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkTargets, setBulkTargets] = useState<BulkUpdateTarget[]>([]);
  const fetched = useRef(false);

  const agents = useAgentsStore((s) => s.agents);
  const standardVersion = useAgentsStore((s) => s.standardVersion);
  const fetchAgents = useAgentsStore((s) => s.fetchAgents);

  // Fetch agents once on mount to populate the store
  useEffect(() => {
    if (!fetched.current) {
      fetched.current = true;
      fetchAgents().catch(() => {});
    }
  }, [fetchAgents]);

  const outdatedAgents = agents.filter(
    (a) => a.status === 'online' && a.version && a.version !== standardVersion,
  );

  // Show the warning banner only when there are outdated agents and it
  // hasn't been dismissed — but keep the component mounted so the bulk
  // progress modal survives agents becoming up-to-date mid-update.
  const showBanner = Boolean(standardVersion) && outdatedAgents.length > 0 && !dismissed;

  const handleUpdateAll = async () => {
    setUpdating(true);
    // Snapshot the targets now — the banner disappears once versions update.
    const targets: BulkUpdateTarget[] = outdatedAgents.map((a) => ({ id: a.id, name: a.name }));
    try {
      const results = await Promise.allSettled(
        outdatedAgents.map((a) => agentsApi.triggerUpdate(a.id)),
      );
      // Only track agents whose update command was actually accepted.
      const accepted = targets.filter((_, i) => results[i].status === 'fulfilled');
      const rejected = results.length - accepted.length;
      if (rejected > 0) {
        message.warning(`Could not start ${rejected} update(s); tracking ${accepted.length}.`);
      }
      if (accepted.length > 0) {
        setBulkTargets(accepted);
        setBulkOpen(true);
      } else {
        message.error('Failed to start any agent updates');
      }
    } catch {
      message.error('Failed to trigger agent updates');
    } finally {
      setUpdating(false);
    }
  };

  const handleBulkClose = () => {
    setBulkOpen(false);
    // Pick up new versions (banner hides once all agents are current).
    fetchAgents().catch(() => {});
  };

  return (
    <>
      {showBanner && (
    <Alert
      type="warning"
      banner
      closable
      onClose={() => setDismissed(true)}
      message={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Space>
            <span>
              {outdatedAgents.length} agent{outdatedAgents.length !== 1 ? 's' : ''} running
              outdated version{outdatedAgents.length !== 1 ? 's' : ''}
            </span>
            <Button type="link" size="small" style={{ padding: 0 }} onClick={() => navigate('/admin/settings')}>
              View Agents
            </Button>
          </Space>
          <Button
            size="small"
            type="primary"
            icon={<CloudUploadOutlined />}
            loading={updating}
            onClick={handleUpdateAll}
          >
            Update All to v{standardVersion}
          </Button>
        </div>
      }
    />
      )}
      <BulkAgentUpdateModal
        open={bulkOpen}
        targets={bulkTargets}
        targetVersion={standardVersion}
        onClose={handleBulkClose}
      />
    </>
  );
};

export default AgentVersionBanner;
