/**
 * Step 4: Protocol Selection
 */

import React from 'react';
import { Typography, Switch, Row, Col, Card, Checkbox, Space } from 'antd';
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
    </div>
  );
};

export default ProtocolSelectionStep;
