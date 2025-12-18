/**
 * Step 3: Vendor Selection
 */

import React from 'react';
import { Typography, Switch, Row, Col, Card, Checkbox, Space } from 'antd';
import { RobotOutlined, CheckCircleFilled } from '@ant-design/icons';
import { useAIScenarioWizardStore } from '../../stores/aiScenarioWizardStore';

const { Title, Text, Paragraph } = Typography;

interface VendorOption {
  id: string;
  name: string;
  aka: string;
}

interface Props {
  vendors: VendorOption[];
}

const VendorSelectionStep: React.FC<Props> = ({ vendors }) => {
  const {
    letAiDecideVendors,
    selectedVendors,
    setLetAiDecideVendors,
    toggleVendor,
  } = useAIScenarioWizardStore();

  return (
    <div>
      <Title level={4} style={{ color: '#e0e8f0', marginBottom: 8 }}>
        Select Device Vendors
      </Title>

      <Paragraph style={{ color: '#8aa4bc', marginBottom: 24 }}>
        Choose which vendors' devices should be included in the scenario.
        Each vendor has unique protocol implementations and fingerprints.
      </Paragraph>

      {/* AI Decision Toggle */}
      <Card
        style={{
          backgroundColor: letAiDecideVendors ? '#2a3f54' : '#1e2d3d',
          borderColor: letAiDecideVendors ? '#5a9fd4' : '#2a3f54',
          marginBottom: 24,
        }}
        styles={{ body: { padding: 16 } }}
      >
        <Space align="center">
          <Switch
            checked={letAiDecideVendors}
            onChange={setLetAiDecideVendors}
          />
          <RobotOutlined style={{ color: '#5a9fd4', fontSize: 20 }} />
          <div>
            <Text strong style={{ color: '#e0e8f0' }}>
              Let AI decide vendors
            </Text>
            <br />
            <Text style={{ color: '#8aa4bc', fontSize: 13 }}>
              AI will select appropriate vendors based on your description and vertical
            </Text>
          </div>
        </Space>
      </Card>

      {/* Manual Vendor Selection */}
      {!letAiDecideVendors && (
        <Row gutter={[12, 12]}>
          {vendors.map(vendor => {
            const isSelected = selectedVendors.includes(vendor.id);
            return (
              <Col span={8} key={vendor.id}>
                <Card
                  hoverable
                  onClick={() => toggleVendor(vendor.id)}
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
                        onChange={() => toggleVendor(vendor.id)}
                      />
                      <Text strong style={{ color: '#e0e8f0' }}>
                        {vendor.name}
                      </Text>
                      <br />
                      <Text style={{ color: '#8aa4bc', fontSize: 12, marginLeft: 24 }}>
                        {vendor.aka}
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

      {!letAiDecideVendors && selectedVendors.length === 0 && (
        <Text style={{ color: '#faad14', marginTop: 16, display: 'block' }}>
          Please select at least one vendor
        </Text>
      )}
    </div>
  );
};

export default VendorSelectionStep;
