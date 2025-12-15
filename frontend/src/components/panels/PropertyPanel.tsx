/**
 * Right sidebar property panel
 * Context-aware panel that shows appropriate forms based on selection
 */

import React from 'react';
import { Typography, Empty } from 'antd';
import { ControlOutlined } from '@ant-design/icons';
import { useUIStore } from '../../stores/uiStore';
import DevicePropertyForm from './DevicePropertyForm';
import FlowPropertyForm from './FlowPropertyForm';

const { Text } = Typography;

const PropertyPanel: React.FC = () => {
  const activePropertyContext = useUIStore((state) => state.activePropertyContext);

  return (
    <div
      style={{
        width: '320px',
        height: '100%',
        background: '#1e2d3d',
        borderLeft: '1px solid #2a3f54',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '16px',
          borderBottom: '1px solid #2a3f54',
          background: '#1a2734',
        }}
      >
        <Text strong style={{ fontSize: '16px', color: '#e0e8f0' }}>
          Properties
        </Text>
      </div>

      {/* Content */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
        }}
      >
        {!activePropertyContext.type || activePropertyContext.ids.length === 0 ? (
          <Empty
            image={<ControlOutlined style={{ fontSize: 48, color: '#4a6a8a' }} />}
            description={
              <div>
                <Text style={{ fontSize: '13px', color: '#8aa4bc' }}>
                  No selection
                </Text>
                <div style={{ marginTop: '8px' }}>
                  <Text style={{ fontSize: '11px', color: '#6a8caf' }}>
                    Click on a device or flow to view and edit its properties
                  </Text>
                </div>
              </div>
            }
            style={{ marginTop: '80px' }}
          />
        ) : activePropertyContext.type === 'device' ? (
          <DevicePropertyForm deviceId={activePropertyContext.ids[0]} />
        ) : activePropertyContext.type === 'flow' ? (
          <FlowPropertyForm flowId={activePropertyContext.ids[0]} />
        ) : activePropertyContext.type === 'multi' ? (
          <Empty
            description={
              <div>
                <Text style={{ fontSize: '13px', color: '#8aa4bc' }}>
                  Multiple items selected
                </Text>
                <div style={{ marginTop: '8px' }}>
                  <Text style={{ fontSize: '11px', color: '#6a8caf' }}>
                    Bulk editing is not yet supported
                  </Text>
                </div>
              </div>
            }
            style={{ marginTop: '80px' }}
          />
        ) : null}
      </div>
    </div>
  );
};

export default PropertyPanel;
