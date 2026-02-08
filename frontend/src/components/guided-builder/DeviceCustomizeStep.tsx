/**
 * Step 4 — Customize device names and vendor/model assignments.
 */

import React, { useState, useMemo } from 'react';
import { Table, Tag, Input, Select, Button, Space, Typography, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { EditOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useGuidedBuilderStore } from '../../stores/guidedBuilderStore';
import type { TemplateDevicePreview } from '../../stores/guidedBuilderStore';
import { listVendors, getVendorModels } from '../../api/fingerprints';
import { DEVICE_TYPE_COLORS_EXTENDED } from '../../constants/protocols';
import { getProtocolColor, getProtocolLabel } from '../../utils/formatUtils';

const { Title, Text } = Typography;

/** Row data with effective (customized) values merged in. */
interface DeviceRow extends TemplateDevicePreview {
  effectiveName: string;
  effectiveVendor: string | undefined;
  effectiveModel: string | undefined;
  isDuplicateName: boolean;
}

const DeviceCustomizeStep: React.FC = () => {
  const {
    expandedDevices,
    customizations,
    setCustomization,
    applyBulkRename,
  } = useGuidedBuilderStore();

  const [bulkPrefix, setBulkPrefix] = useState('');

  // Vendor list for dropdown
  const { data: vendors } = useQuery({
    queryKey: ['fingerprint-vendors'],
    queryFn: () => listVendors(),
  });

  // Build effective rows with duplicate detection
  const rows: DeviceRow[] = useMemo(() => {
    const effective = expandedDevices.map((d) => {
      const c = customizations[d.uid];
      return {
        ...d,
        effectiveName: c?.name ?? d.name,
        effectiveVendor: c?.vendor ?? d.vendor,
        effectiveModel: c?.fingerprintModel ?? d.fingerprintModel,
        isDuplicateName: false,
      };
    });

    // Check for duplicates
    const nameCounts = new Map<string, number>();
    for (const r of effective) {
      nameCounts.set(r.effectiveName, (nameCounts.get(r.effectiveName) ?? 0) + 1);
    }
    for (const r of effective) {
      r.isDuplicateName = (nameCounts.get(r.effectiveName) ?? 0) > 1;
    }

    return effective;
  }, [expandedDevices, customizations]);

  const columns: ColumnsType<DeviceRow> = [
    {
      title: 'Name',
      key: 'name',
      width: 220,
      render: (_: unknown, row: DeviceRow) => (
        <Tooltip title={row.isDuplicateName ? 'Duplicate device name' : undefined}>
          <Input
            size="small"
            value={row.effectiveName}
            status={row.isDuplicateName ? 'error' : undefined}
            onChange={(e) => setCustomization(row.uid, { name: e.target.value })}
            style={{ width: '100%' }}
          />
        </Tooltip>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      width: 90,
      render: (type: string) => (
        <Tag color={DEVICE_TYPE_COLORS_EXTENDED[type] ?? '#8c8c8c'}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Vendor',
      key: 'vendor',
      width: 180,
      render: (_: unknown, row: DeviceRow) => (
        <VendorSelect
          value={row.effectiveVendor}
          vendors={vendors}
          onChange={(vendor) => {
            setCustomization(row.uid, { vendor, fingerprintModel: undefined });
          }}
        />
      ),
    },
    {
      title: 'Model',
      key: 'model',
      width: 180,
      render: (_: unknown, row: DeviceRow) => (
        <ModelSelect
          vendor={row.effectiveVendor}
          value={row.effectiveModel}
          onChange={(model) => setCustomization(row.uid, { fingerprintModel: model })}
        />
      ),
    },
    {
      title: 'Zone',
      dataIndex: 'zone',
      key: 'zone',
      width: 110,
      render: (z: string | undefined) => (
        <span style={{ color: z ? '#c9d1d9' : '#555' }}>{z ?? '—'}</span>
      ),
    },
    {
      title: 'Protocols',
      dataIndex: 'protocols',
      key: 'protocols',
      render: (protocols: string[]) => (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {protocols.map((p) => (
            <Tag key={p} color={getProtocolColor(p)} style={{ fontSize: 11 }}>
              {getProtocolLabel(p)}
            </Tag>
          ))}
        </div>
      ),
    },
  ];

  const duplicateCount = rows.filter((r) => r.isDuplicateName).length;

  return (
    <div>
      <Title level={5} style={{ color: '#e0e8f0', marginBottom: 8 }}>
        Customize Devices
      </Title>
      <Text style={{ color: '#8aa4bc', display: 'block', marginBottom: 16 }}>
        Edit device names and vendor/model assignments. This step is optional — defaults from the template work well.
      </Text>

      {/* Bulk rename */}
      <Space style={{ marginBottom: 16 }}>
        <Input
          size="small"
          placeholder="Name prefix (e.g. PLC)"
          value={bulkPrefix}
          onChange={(e) => setBulkPrefix(e.target.value)}
          style={{ width: 200 }}
        />
        <Button
          size="small"
          icon={<EditOutlined />}
          disabled={!bulkPrefix.trim()}
          onClick={() => {
            applyBulkRename(bulkPrefix.trim());
            setBulkPrefix('');
          }}
        >
          Bulk Rename All
        </Button>
        {duplicateCount > 0 && (
          <Text type="danger" style={{ fontSize: 12 }}>
            {duplicateCount} device{duplicateCount !== 1 ? 's' : ''} with duplicate names
          </Text>
        )}
      </Space>

      <Table
        dataSource={rows}
        columns={columns}
        rowKey="uid"
        pagination={false}
        size="small"
        scroll={{ y: 380 }}
        style={{ backgroundColor: '#141428' }}
      />
    </div>
  );
};

// ---------------------------------------------------------------------------
// Helper sub-components
// ---------------------------------------------------------------------------

interface VendorSelectProps {
  value: string | undefined;
  vendors: { vendor: string; display_name: string }[] | undefined;
  onChange: (vendor: string) => void;
}

const VendorSelect: React.FC<VendorSelectProps> = ({ value, vendors, onChange }) => (
  <Select
    size="small"
    showSearch
    value={value}
    placeholder="Vendor"
    style={{ width: '100%' }}
    onChange={onChange}
    filterOption={(input, option) =>
      (option?.label as string)?.toLowerCase().includes(input.toLowerCase()) ?? false
    }
    options={(vendors ?? []).map((v) => ({
      value: v.vendor,
      label: v.display_name,
    }))}
  />
);

interface ModelSelectProps {
  vendor: string | undefined;
  value: string | undefined;
  onChange: (model: string) => void;
}

const ModelSelect: React.FC<ModelSelectProps> = ({ vendor, value, onChange }) => {
  const { data: models } = useQuery({
    queryKey: ['fingerprint-vendor-models', vendor],
    queryFn: () => getVendorModels(vendor!),
    enabled: !!vendor,
  });

  return (
    <Select
      size="small"
      showSearch
      value={value}
      placeholder={vendor ? 'Model' : 'Select vendor first'}
      disabled={!vendor}
      style={{ width: '100%' }}
      onChange={onChange}
      filterOption={(input, option) =>
        (option?.label as string)?.toLowerCase().includes(input.toLowerCase()) ?? false
      }
      options={(models ?? []).map((m) => ({ value: m, label: m }))}
    />
  );
};

export default DeviceCustomizeStep;
