/**
 * Left sidebar device palette
 * Displays draggable device templates grouped by type
 */

import React, { useState } from 'react';
import { Input, Collapse, Typography, Spin, Empty } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import PaletteItem from './PaletteItem';
import { devicesApi } from '../../api/devices';
import type { DeviceProfile } from '../../types';
import {
  getDeviceTypeMeta,
  DEVICE_CATEGORY_LABELS,
  CATEGORY_ORDER,
  DeviceCategory,
} from '../../constants/deviceTypeRegistry';

const { Text } = Typography;
const { Panel } = Collapse;

const DevicePalette: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['device-profiles', { builtin_only: true }],
    queryFn: () => devicesApi.list({ builtin_only: true, page_size: 100 }),
  });

  const devices = data?.items || [];

  // Filter devices by search term
  const filteredDevices = devices.filter((device) => {
    const search = searchTerm.toLowerCase();
    return (
      device.name.toLowerCase().includes(search) ||
      device.device_type.toLowerCase().includes(search) ||
      device.role?.toLowerCase().includes(search)
    );
  });

  // Group devices by category
  const groupedByCategory = filteredDevices.reduce((acc, device) => {
    const meta = getDeviceTypeMeta(device.device_type);
    const cat = meta.category;
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(device);
    return acc;
  }, {} as Record<DeviceCategory, DeviceProfile[]>);

  return (
    <div
      style={{
        width: '280px',
        height: '100%',
        background: '#1e2d3d',
        borderRight: '1px solid #2a3f54',
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
        <Text strong style={{ fontSize: '16px', display: 'block', marginBottom: '12px', color: '#e0e8f0' }}>
          Device Library
        </Text>
        <Input
          placeholder="Search devices..."
          prefix={<SearchOutlined style={{ color: '#6a8caf' }} />}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          allowClear
          style={{ background: '#253545', borderColor: '#3a5068' }}
        />
      </div>

      {/* Device list */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px',
        }}
      >
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin />
          </div>
        ) : error ? (
          <Empty
            description="Failed to load devices"
            style={{ marginTop: '40px' }}
          />
        ) : filteredDevices.length === 0 ? (
          <Empty
            description={searchTerm ? 'No devices found' : 'No devices available'}
            style={{ marginTop: '40px' }}
          />
        ) : (
          <Collapse
            defaultActiveKey={[CATEGORY_ORDER[0]]}
            ghost
            expandIconPosition="end"
          >
            {CATEGORY_ORDER.map((cat) => {
              const devicesInCategory = groupedByCategory[cat];
              if (!devicesInCategory || devicesInCategory.length === 0) return null;

              return (
                <Panel
                  header={
                    <Text strong style={{ fontSize: '13px', color: '#b8c9dc' }}>
                      {DEVICE_CATEGORY_LABELS[cat]} ({devicesInCategory.length})
                    </Text>
                  }
                  key={cat}
                >
                  {devicesInCategory.map((device) => (
                    <PaletteItem key={device.id} device={device} />
                  ))}
                </Panel>
              );
            })}
          </Collapse>
        )}
      </div>

      {/* Footer hint */}
      <div
        style={{
          padding: '12px',
          borderTop: '1px solid #2a3f54',
          background: '#1a2734',
        }}
      >
        <Text
          style={{
            fontSize: '11px',
            display: 'block',
            textAlign: 'center',
            color: '#6a8caf',
          }}
        >
          Drag devices onto the canvas
        </Text>
      </div>
    </div>
  );
};

export default DevicePalette;
