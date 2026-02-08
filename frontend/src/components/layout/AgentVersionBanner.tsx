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

const AgentVersionBanner: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [dismissed, setDismissed] = useState(false);
  const [updating, setUpdating] = useState(false);
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

  if (!standardVersion || outdatedAgents.length === 0 || dismissed) {
    return null;
  }

  const handleUpdateAll = async () => {
    setUpdating(true);
    try {
      const results = await Promise.allSettled(
        outdatedAgents.map((a) => agentsApi.triggerUpdate(a.id)),
      );
      const succeeded = results.filter((r) => r.status === 'fulfilled').length;
      const failed = results.length - succeeded;
      if (failed === 0) {
        message.success(`Update triggered for ${succeeded} agent(s)`);
      } else {
        message.warning(`Updated ${succeeded}, failed ${failed} agent(s)`);
      }
      // Refresh agent list after a delay to pick up new versions
      setTimeout(() => fetchAgents().catch(() => {}), 3000);
    } catch {
      message.error('Failed to trigger agent updates');
    } finally {
      setUpdating(false);
    }
  };

  return (
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
  );
};

export default AgentVersionBanner;
