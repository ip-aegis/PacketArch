/**
 * Modal for generating AI descriptions for scenarios
 */

import React, { useEffect, useState } from 'react';
import { Modal, Input, Space, Typography, Tag, Spin, message, Alert } from 'antd';
import {
  RobotOutlined,
  AppstoreOutlined,
  ApiOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import { aiApi, type GenerateDescriptionResponse } from '../../api/ai';
import { extractErrorMessage } from '../../utils/errorUtils';

const { TextArea } = Input;
const { Text } = Typography;

interface GenerateDescriptionModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (description: string) => Promise<void>;
  scenarioId: string;
  scenarioName: string;
  currentDescription?: string;
}

const GenerateDescriptionModal: React.FC<GenerateDescriptionModalProps> = ({
  open,
  onClose,
  onSave,
  scenarioId,
  scenarioName,
  currentDescription,
}) => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [description, setDescription] = useState('');
  const [metadata, setMetadata] = useState<GenerateDescriptionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Generate description when modal opens
  useEffect(() => {
    if (open && scenarioId) {
      generateDescription();
    }
  }, [open, scenarioId]);

  const generateDescription = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await aiApi.generateDescription(scenarioId);
      setDescription(result.description);
      setMetadata(result);
    } catch (err: unknown) {
      console.error('Failed to generate description:', err);
      setError(extractErrorMessage(err, 'Failed to generate description'));
      // Fall back to current description if generation fails
      if (currentDescription) {
        setDescription(currentDescription);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(description);
      message.success('Description updated');
      onClose();
    } catch (err) {
      console.error('Failed to save description:', err);
      message.error('Failed to save description');
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    setDescription('');
    setMetadata(null);
    setError(null);
    onClose();
  };

  return (
    <Modal
      title={
        <Space>
          <RobotOutlined style={{ color: '#1890ff' }} />
          <span>Generate AI Description</span>
        </Space>
      }
      open={open}
      onCancel={handleClose}
      onOk={handleSave}
      okText="Save Description"
      okButtonProps={{ loading: saving, disabled: loading || !description }}
      cancelText="Cancel"
      width={560}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* Scenario Name */}
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>Scenario</Text>
          <div>
            <Text strong>{scenarioName}</Text>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert
            type="warning"
            message="Generation Issue"
            description={error}
            showIcon
            action={
              <a onClick={generateDescription} style={{ fontSize: 12 }}>
                Retry
              </a>
            }
          />
        )}

        {/* Loading State */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: 32 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">Analyzing scenario and generating description...</Text>
            </div>
          </div>
        ) : (
          <>
            {/* Scenario Stats */}
            {metadata && (
              <Space size={8} wrap>
                <Tag icon={<AppstoreOutlined />} color="blue">
                  {metadata.device_count} device{metadata.device_count !== 1 ? 's' : ''}
                </Tag>
                <Tag icon={<NodeIndexOutlined />} color="green">
                  {metadata.flow_count} flow{metadata.flow_count !== 1 ? 's' : ''}
                </Tag>
                {metadata.protocols.length > 0 && (
                  <Tag icon={<ApiOutlined />} color="purple">
                    {metadata.protocols.join(', ')}
                  </Tag>
                )}
              </Space>
            )}

            {/* Description TextArea */}
            <div>
              <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                Generated Description (editable)
              </Text>
              <TextArea
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="AI-generated description will appear here..."
                style={{ resize: 'vertical' }}
              />
            </div>

            {/* Regenerate Link */}
            {metadata && (
              <div style={{ textAlign: 'right' }}>
                <a
                  onClick={generateDescription}
                  style={{ fontSize: 12 }}
                >
                  <RobotOutlined /> Regenerate
                </a>
              </div>
            )}
          </>
        )}
      </Space>
    </Modal>
  );
};

export default GenerateDescriptionModal;
