/**
 * Right sidebar property panel
 * Context-aware panel that shows appropriate forms based on selection
 */

import React from 'react';
import { Typography } from 'antd';
import { ControlOutlined } from '@ant-design/icons';
import { EmptyState } from '../common';
import { useUIStore } from '../../stores/uiStore';
import DevicePropertyForm from './DevicePropertyForm';
import FlowPropertyForm from './FlowPropertyForm';
import ZonePropertyForm from './ZonePropertyForm';

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
          <EmptyState
            icon={<ControlOutlined />}
            message="No selection"
            hint="Click on a device or flow to view and edit its properties"
            marginTop={80}
          />
        ) : activePropertyContext.type === 'device' ? (
          <DevicePropertyForm deviceId={activePropertyContext.ids[0]} />
        ) : activePropertyContext.type === 'flow' ? (
          <FlowPropertyForm flowId={activePropertyContext.ids[0]} />
        ) : activePropertyContext.type === 'zone' ? (
          <ZonePropertyForm zoneId={activePropertyContext.ids[0]} />
        ) : activePropertyContext.type === 'multi' ? (
          <EmptyState
            message="Multiple items selected"
            hint="Bulk editing is not yet supported"
            marginTop={80}
          />
        ) : null}
      </div>
    </div>
  );
};

export default PropertyPanel;
