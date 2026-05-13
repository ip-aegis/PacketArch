/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Step 4: Protocol Selection
 */

import React from 'react';
import { Typography, Switch, Row, Col, Card, Checkbox, Space, Radio } from 'antd';
import { RobotOutlined, CheckCircleFilled } from '@ant-design/icons';
import { useAIScenarioWizardStore } from '../../stores/aiScenarioWizardStore';

const { Title, Text, Paragraph } = Typography;

interface ProtocolOption {
  id: string;
  name: string;
  description: string;
}

interface Props {
  protocols: ProtocolOption[];
}

const ProtocolSelectionStep: React.FC<Props> = ({ protocols }) => {
  const {
    letAiDecideProtocols,
    selectedProtocols,
    setLetAiDecideProtocols,
    toggleProtocol,
    cellIsolationMode,
    setCellIsolationMode,
  } = useAIScenarioWizardStore();

  return (
    <div>
      <Title level={4} style={{ color: '#e0e8f0', marginBottom: 8 }}>
        Select Communication Protocols
      </Title>

      <Paragraph style={{ color: '#8aa4bc', marginBottom: 24 }}>
        Choose which industrial protocols should be used for device communication.
        Different protocols are typical for different industries.
      </Paragraph>

      {/* AI Decision Toggle */}
      <Card
        style={{
          backgroundColor: letAiDecideProtocols ? '#2a3f54' : '#1e2d3d',
          borderColor: letAiDecideProtocols ? '#5a9fd4' : '#2a3f54',
          marginBottom: 24,
        }}
        styles={{ body: { padding: 16 } }}
      >
        <Space align="center">
          <Switch
            checked={letAiDecideProtocols}
            onChange={setLetAiDecideProtocols}
          />
          <RobotOutlined style={{ color: '#5a9fd4', fontSize: 20 }} />
          <div>
            <Text strong style={{ color: '#e0e8f0' }}>
              Let AI decide protocols
            </Text>
            <br />
            <Text style={{ color: '#8aa4bc', fontSize: 13 }}>
              AI will select appropriate protocols based on your description, vendors, and vertical
            </Text>
          </div>
        </Space>
      </Card>

      {/* Manual Protocol Selection */}
      {!letAiDecideProtocols && (
        <Row gutter={[12, 12]}>
          {protocols.map(protocol => {
            const isSelected = selectedProtocols.includes(protocol.id);
            return (
              <Col span={8} key={protocol.id}>
                <Card
                  hoverable
                  onClick={() => toggleProtocol(protocol.id)}
                  style={{
                    backgroundColor: isSelected ? '#2a3f54' : '#1e2d3d',
                    borderColor: isSelected ? '#5a9fd4' : '#2a3f54',
                    cursor: 'pointer',
                    height: '100%',
                  }}
                  styles={{ body: { padding: 12 } }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <Checkbox
                        checked={isSelected}
                        style={{ marginRight: 8 }}
                        onClick={e => e.stopPropagation()}
                        onChange={() => toggleProtocol(protocol.id)}
                      />
                      <Text strong style={{ color: '#e0e8f0' }}>
                        {protocol.name}
                      </Text>
                      <br />
                      <Text style={{ color: '#8aa4bc', fontSize: 12, marginLeft: 24 }}>
                        {protocol.description}
                      </Text>
                    </div>
                    {isSelected && (
                      <CheckCircleFilled style={{ color: '#52c41a' }} />
                    )}
                  </div>
                </Card>
              </Col>
            );
          })}
        </Row>
      )}

      {!letAiDecideProtocols && selectedProtocols.length === 0 && (
        <Text style={{ color: '#faad14', marginTop: 16, display: 'block' }}>
          Please select at least one protocol
        </Text>
      )}

      {/* Purdue cell-isolation default mode */}
      <Card
        style={{
          marginTop: 24,
          backgroundColor: '#1e2d3d',
          borderColor: '#2a3f54',
        }}
        bodyStyle={{ padding: 16 }}
      >
        <Title level={5} style={{ color: '#e0e8f0', marginTop: 0 }}>
          Cell Isolation (Purdue L0–L2)
        </Title>
        <Text style={{ color: '#8aa4bc', display: 'block', marginBottom: 12 }}>
          Sets the default east/west enforcement for the generated scenario.
          AI will author flows and conduits to match the chosen mode.
        </Text>
        <Radio.Group
          value={cellIsolationMode}
          onChange={(e) => setCellIsolationMode(e.target.value)}
        >
          <Space direction="vertical">
            <Radio value="off">
              <Text style={{ color: '#e0e8f0' }}>Off</Text>{' '}
              <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
                — permissive. Cells may talk freely.
              </Text>
            </Radio>
            <Radio value="conduit_gated">
              <Text style={{ color: '#e0e8f0' }}>Conduit-gated</Text>{' '}
              <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
                — every cell↔cell flow needs an explicit allowing conduit.
              </Text>
            </Radio>
            <Radio value="strict_northbound">
              <Text style={{ color: '#e0e8f0' }}>Strict — northbound only</Text>{' '}
              <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
                — no east/west cell traffic. Cells only talk to L3+ zones.
                Most realistic for IEC 62443.
              </Text>
            </Radio>
          </Space>
        </Radio.Group>
      </Card>
    </div>
  );
};

export default ProtocolSelectionStep;
