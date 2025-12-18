/**
 * Step 2: Natural Language Description
 */

import React from 'react';
import { Input, Typography, Space, Tag } from 'antd';
import { BulbOutlined } from '@ant-design/icons';
import { useAIScenarioWizardStore } from '../../stores/aiScenarioWizardStore';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const EXAMPLES = [
  'A manufacturing cell with 3 Rockwell PLCs controlling 10 VFDs and 2 HMIs',
  'Water treatment plant with RTUs monitoring 5 pump stations via Modbus',
  'Power substation with DNP3 RTUs and IEC 104 connections to control center',
  'Oil pipeline SCADA with 8 remote sites using Modbus TCP polling',
];

const DescriptionStep: React.FC = () => {
  const { description, vertical, setDescription } = useAIScenarioWizardStore();

  const getContextualPlaceholder = () => {
    switch (vertical) {
      case 'manufacturing':
        return 'Describe your manufacturing environment...\n\nExample: "A bottling line with 5 Siemens S7 PLCs controlling conveyor belts, 3 HMIs for operators, and 15 VFDs for motor control. Include PROFINET communication."';
      case 'water':
        return 'Describe your water/wastewater system...\n\nExample: "A water distribution system with a central SCADA server polling 12 remote pump stations via Modbus TCP. Include flow meters and pressure sensors at each site."';
      case 'energy':
        return 'Describe your power system...\n\nExample: "A 138kV substation with 8 protective relays, an RTU for SCADA communication via DNP3, and local HMI for operators."';
      case 'oil_gas':
        return 'Describe your oil & gas system...\n\nExample: "A pipeline compressor station with PLCs controlling 3 compressor units, safety instrumented systems, and SCADA connection to dispatch center."';
      default:
        return 'Describe the OT environment you want to simulate...';
    }
  };

  return (
    <div>
      <Title level={4} style={{ color: '#e0e8f0', marginBottom: 8 }}>
        Describe Your Environment
      </Title>

      <Paragraph style={{ color: '#8aa4bc', marginBottom: 24 }}>
        Describe the OT environment you want to simulate in natural language.
        Include device types, quantities, vendors, and communication patterns.
      </Paragraph>

      <TextArea
        value={description}
        onChange={e => setDescription(e.target.value)}
        placeholder={getContextualPlaceholder()}
        rows={8}
        style={{
          backgroundColor: '#1e2d3d',
          borderColor: '#2a3f54',
          color: '#e0e8f0',
          fontSize: 14,
        }}
      />

      <div style={{ marginTop: 24 }}>
        <Space align="center" style={{ marginBottom: 12 }}>
          <BulbOutlined style={{ color: '#faad14' }} />
          <Text style={{ color: '#8aa4bc' }}>Example descriptions:</Text>
        </Space>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {EXAMPLES.map((example, index) => (
            <Tag
              key={index}
              style={{
                backgroundColor: '#1e2d3d',
                borderColor: '#2a3f54',
                color: '#8aa4bc',
                cursor: 'pointer',
                maxWidth: '100%',
                whiteSpace: 'normal',
                height: 'auto',
                padding: '4px 8px',
              }}
              onClick={() => setDescription(example)}
            >
              {example.length > 60 ? `${example.substring(0, 60)}...` : example}
            </Tag>
          ))}
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <Text style={{ color: '#52c41a', fontSize: 12 }}>
          Minimum 10 characters required ({description.length}/10)
        </Text>
      </div>
    </div>
  );
};

export default DescriptionStep;
