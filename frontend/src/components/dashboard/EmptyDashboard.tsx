/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React from 'react';
import { CloudServerOutlined } from '@ant-design/icons';
import { EmptyState } from '../common';

const EmptyDashboard: React.FC = () => {
  return (
    <div
      style={{
        padding: '80px 24px',
        background: '#1a1a2e',
        border: '1px solid #2d2d52',
        borderRadius: 8,
      }}
    >
      <EmptyState
        icon={<CloudServerOutlined />}
        message="No active deployments"
        hint="Deploy a scenario to an agent to see live traffic metrics here."
        marginTop={0}
        actions={[
          { label: 'Go to Deployments', primary: true, to: '/deployments' },
        ]}
        helpArticleId="live-traffic"
      />
    </div>
  );
};

export default EmptyDashboard;
