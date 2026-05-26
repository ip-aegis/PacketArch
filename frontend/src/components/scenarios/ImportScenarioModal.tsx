/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * ImportScenarioModal - Upload and import a JSON scenario file.
 */

import React, { useState } from 'react';
import { Modal, Button, Space, Typography, Card, Upload, App, Tag } from 'antd';
import { ImportOutlined, InboxOutlined } from '@ant-design/icons';
import type { ImportedScenarioData } from '../../hooks/useScenarioMutations';
import { verticalConfig } from './scenarioConstants';

const { Dragger } = Upload;
const { Text } = Typography;

interface FilePreview {
  data: ImportedScenarioData;
  deviceCount: number;
  flowCount: number;
  zoneCount: number;
}

/**
 * Detect which format the uploaded JSON document is.
 *
 *   portable — public authoring format. Required:
 *              format_version === "1.0", name, zones[], devices[], flows[].
 *   legacy   — previously-exported scenario. Required: name, definition.
 *
 * Returns a FilePreview when detection succeeds, or a string error message.
 */
function detectAndParse(raw: unknown): FilePreview | string {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return 'File is not a JSON object.';
  }
  const obj = raw as Record<string, unknown>;

  const looksPortable =
    obj.format_version === '1.0' &&
    Array.isArray(obj.zones) &&
    Array.isArray(obj.devices) &&
    Array.isArray(obj.flows);

  if (looksPortable) {
    if (typeof obj.name !== 'string' || !obj.name) {
      return 'Portable scenario is missing required field: name.';
    }
    return {
      data: {
        format: 'portable',
        payload: obj as { name: string; [key: string]: unknown },
      },
      deviceCount: (obj.devices as unknown[]).length,
      flowCount: (obj.flows as unknown[]).length,
      zoneCount: (obj.zones as unknown[]).length,
    };
  }

  // Legacy export shape
  if (obj.name && obj.definition && typeof obj.definition === 'object') {
    const def = obj.definition as Record<string, unknown>;
    const devices = (def.devices ?? {}) as Record<string, unknown>;
    const flows = (def.flows ?? {}) as Record<string, unknown>;
    const zones = (def.zones ?? {}) as Record<string, unknown>;
    return {
      data: {
        format: 'legacy',
        payload: obj as {
          name: string;
          definition: Record<string, unknown>;
          [key: string]: unknown;
        },
      },
      deviceCount: Object.keys(devices).length,
      flowCount: Object.keys(flows).length,
      zoneCount: Object.keys(zones).length,
    };
  }

  return (
    'Unrecognized scenario file. Expected either a PacketArch export ' +
    '(top-level "name" + "definition") or a portable scenario ' +
    '(format_version "1.0" + "zones", "devices", "flows" arrays).'
  );
}

export interface ImportScenarioModalProps {
  open: boolean;
  loading: boolean;
  onCancel: () => void;
  onImport: (data: ImportedScenarioData) => void;
}

const ImportScenarioModal: React.FC<ImportScenarioModalProps> = ({
  open,
  loading,
  onCancel,
  onImport,
}) => {
  const { message } = App.useApp();
  const [filePreview, setFilePreview] = useState<FilePreview | null>(null);

  const handleCancel = () => {
    setFilePreview(null);
    onCancel();
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background:
                'linear-gradient(135deg, #722ed120 0%, #722ed110 100%)',
              border: '1px solid #722ed140',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#722ed1',
            }}
          >
            <ImportOutlined style={{ fontSize: 18 }} />
          </div>
          <span style={{ color: '#fff', fontSize: 16 }}>
            Import Scenario
          </span>
        </div>
      }
      open={open}
      onCancel={handleCancel}
      footer={
        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
          <Button onClick={handleCancel}>Cancel</Button>
          <Button
            type="primary"
            disabled={!filePreview}
            loading={loading}
            onClick={() => filePreview && onImport(filePreview.data)}
            style={{ background: '#722ed1', borderColor: '#722ed1' }}
          >
            Import Scenario
          </Button>
        </Space>
      }
      styles={{
        header: {
          background: '#141428',
          borderBottom: '1px solid #2d2d52',
        },
        body: { background: '#1a1a2e', padding: 24 },
        content: { background: '#141428' },
      }}
    >
      <Dragger
        name="file"
        accept=".json"
        maxCount={1}
        showUploadList={false}
        beforeUpload={(file) => {
          const reader = new FileReader();
          reader.onload = (e) => {
            try {
              const content = e.target?.result as string;
              const parsed = JSON.parse(content);
              const result = detectAndParse(parsed);
              if (typeof result === 'string') {
                message.error(result);
                return;
              }
              setFilePreview(result);
              const name = result.data.payload.name as string;
              const kind =
                result.data.format === 'portable' ? 'portable' : 'export';
              message.success(`Loaded ${kind} scenario: ${name}`);
            } catch {
              message.error('Invalid JSON file');
            }
          };
          reader.readAsText(file);
          return false; // Prevent auto upload
        }}
        style={{
          background: '#141428',
          border: '1px dashed #2d2d52',
          borderRadius: 8,
        }}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined style={{ color: '#722ed1', fontSize: 48 }} />
        </p>
        <p className="ant-upload-text" style={{ color: '#fff' }}>
          Click or drag a JSON file to import
        </p>
        <p className="ant-upload-hint" style={{ color: '#6b6b8a' }}>
          Accepts both PacketArch exports and portable scenarios
          (.pascenario.json)
        </p>
      </Dragger>

      {filePreview && (
        <Card
          style={{
            marginTop: 16,
            background: '#141428',
            border: '1px solid #2d2d52',
          }}
          bodyStyle={{ padding: 16 }}
        >
          <Space
            style={{
              width: '100%',
              justifyContent: 'space-between',
              marginBottom: 8,
            }}
          >
            <Text strong style={{ color: '#fff' }}>
              Ready to import:
            </Text>
            <Tag color={filePreview.data.format === 'portable' ? 'gold' : 'blue'}>
              {filePreview.data.format === 'portable'
                ? 'Portable v1'
                : 'PacketArch Export'}
            </Tag>
          </Space>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Text style={{ color: '#a8a8c0' }}>
              <strong>Name:</strong>{' '}
              {filePreview.data.payload.name as string}
            </Text>
            {filePreview.data.payload.vertical && (
              <Text style={{ color: '#a8a8c0' }}>
                <strong>Vertical:</strong>{' '}
                {verticalConfig[filePreview.data.payload.vertical as string]
                  ?.label || (filePreview.data.payload.vertical as string)}
              </Text>
            )}
            <Text style={{ color: '#a8a8c0' }}>
              <strong>Contents:</strong> {filePreview.zoneCount} zones,{' '}
              {filePreview.deviceCount} devices, {filePreview.flowCount} flows
            </Text>
            {filePreview.data.format === 'portable' && (
              <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                The importer will resolve any unspecified vendor /
                fingerprint_model values from the local catalog and allocate
                IPs / MACs automatically.
              </Text>
            )}
            {filePreview.data.payload.description && (
              <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                {filePreview.data.payload.description as string}
              </Text>
            )}
          </Space>
        </Card>
      )}
    </Modal>
  );
};

export default ImportScenarioModal;
