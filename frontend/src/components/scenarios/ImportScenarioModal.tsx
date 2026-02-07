/**
 * ImportScenarioModal - Upload and import a JSON scenario file.
 */

import React, { useState } from 'react';
import { Modal, Button, Space, Typography, Card, Upload, App } from 'antd';
import { ImportOutlined, InboxOutlined } from '@ant-design/icons';
import type { ImportedScenarioData } from '../../hooks/useScenarioMutations';
import { verticalConfig } from './scenarioConstants';

const { Dragger } = Upload;
const { Text } = Typography;

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
  const [fileData, setFileData] = useState<ImportedScenarioData | null>(null);

  const handleCancel = () => {
    setFileData(null);
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
            disabled={!fileData}
            loading={loading}
            onClick={() => fileData && onImport(fileData)}
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
              const data = JSON.parse(content);
              if (!data.name || !data.definition) {
                message.error(
                  'Invalid scenario file: missing required fields (name, definition)',
                );
                return;
              }
              setFileData(data);
              message.success(`File loaded: ${data.name}`);
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
          Import a scenario previously exported from PacketArch
        </p>
      </Dragger>

      {fileData && (
        <Card
          style={{
            marginTop: 16,
            background: '#141428',
            border: '1px solid #2d2d52',
          }}
          bodyStyle={{ padding: 16 }}
        >
          <Text
            strong
            style={{
              color: '#fff',
              display: 'block',
              marginBottom: 8,
            }}
          >
            Ready to import:
          </Text>
          <Space direction="vertical" size={4}>
            <Text style={{ color: '#a8a8c0' }}>
              <strong>Name:</strong> {fileData.name}
            </Text>
            {fileData.vertical && (
              <Text style={{ color: '#a8a8c0' }}>
                <strong>Vertical:</strong>{' '}
                {verticalConfig[fileData.vertical]?.label ||
                  fileData.vertical}
              </Text>
            )}
            {fileData.description && (
              <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                {fileData.description}
              </Text>
            )}
          </Space>
        </Card>
      )}
    </Modal>
  );
};

export default ImportScenarioModal;
