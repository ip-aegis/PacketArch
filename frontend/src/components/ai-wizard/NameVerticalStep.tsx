/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Step 1: Name & Vertical Selection
 */

import React from 'react';
import { Input, Typography, Row, Col, Card } from 'antd';
import { CheckCircleFilled } from '@ant-design/icons';
import { useAIScenarioWizardStore } from '../../stores/aiScenarioWizardStore';

const { Title, Text } = Typography;

interface VerticalOption {
  id: string;
  name: string;
  description: string;
}

interface Props {
  verticals: VerticalOption[];
}

const NameVerticalStep: React.FC<Props> = ({ verticals }) => {
  const { scenarioName, vertical, setScenarioName, setVertical } = useAIScenarioWizardStore();

  return (
    <div>
      <Title level={4} style={{ color: '#e0e8f0', marginBottom: 24 }}>
        Name Your Scenario
      </Title>

      <Input
        placeholder="e.g., Manufacturing Line A, Water Treatment Plant"
        value={scenarioName}
        onChange={e => setScenarioName(e.target.value)}
        size="large"
        style={{
          backgroundColor: '#1e2d3d',
          borderColor: '#2a3f54',
          color: '#e0e8f0',
          marginBottom: 32,
        }}
      />

      <Title level={4} style={{ color: '#e0e8f0', marginBottom: 16 }}>
        Select Industry Vertical
      </Title>

      <Row gutter={[16, 16]}>
        {verticals.map(v => (
          <Col span={12} key={v.id}>
            <Card
              hoverable
              onClick={() => setVertical(v.id)}
              style={{
                backgroundColor: vertical === v.id ? '#2a3f54' : '#1e2d3d',
                borderColor: vertical === v.id ? '#5a9fd4' : '#2a3f54',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              styles={{ body: { padding: 16 } }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <Text strong style={{ color: '#e0e8f0', fontSize: 16 }}>
                    {v.name}
                  </Text>
                  <br />
                  <Text style={{ color: '#8aa4bc', fontSize: 13 }}>
                    {v.description}
                  </Text>
                </div>
                {vertical === v.id && (
                  <CheckCircleFilled style={{ color: '#52c41a', fontSize: 20 }} />
                )}
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
};

export default NameVerticalStep;
