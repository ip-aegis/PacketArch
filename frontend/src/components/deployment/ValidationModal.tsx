/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * ValidationModal - Pre-deploy validation results display.
 */

import React from 'react';
import {
  Alert,
  Button,
  Modal,
  Space,
  Tag,
  Typography,
} from 'antd';
import {
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  ToolOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import type { ScenarioValidationResponse } from '../../api/scenarios';

const { Text } = Typography;

export interface ValidationModalProps {
  open: boolean;
  validationResult: ScenarioValidationResponse | null;
  deploymentsLoading: boolean;
  repairing: boolean;
  onCancel: () => void;
  onProceed: () => void;
  onRepair: () => void;
}

const ValidationModal: React.FC<ValidationModalProps> = React.memo(({
  open,
  validationResult,
  deploymentsLoading,
  repairing,
  onCancel,
  onProceed,
  onRepair,
}) => {
  const hasProtocolMismatchWarnings = validationResult?.warnings.some(
    (w) => w.code === 'protocol_identity_mismatch',
  );

  return (
    <Modal
      title={
        <Space>
          {validationResult?.is_valid ? (
            <WarningOutlined style={{ color: '#faad14' }} />
          ) : (
            <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
          )}
          <span>Scenario Validation</span>
        </Space>
      }
      open={open}
      onCancel={onCancel}
      footer={
        <Space>
          <Button onClick={onCancel}>Cancel</Button>
          {hasProtocolMismatchWarnings && (
            <Button
              icon={<ToolOutlined />}
              onClick={onRepair}
              loading={repairing}
            >
              Repair Protocols
            </Button>
          )}
          {validationResult?.is_valid && (
            <Button
              type="primary"
              onClick={onProceed}
              loading={deploymentsLoading}
            >
              Deploy Anyway
            </Button>
          )}
        </Space>
      }
      width={600}
    >
      {validationResult && (
        <div>
          {/* Summary Stats */}
          <div
            style={{
              marginBottom: 16,
              display: 'flex',
              gap: 16,
            }}
          >
            <Tag color="blue">
              {validationResult.device_count} Devices
            </Tag>
            <Tag color="green">
              {validationResult.flow_count} Flows
            </Tag>
            {validationResult.protocols_used.length > 0 && (
              <Tag color="purple">
                {validationResult.protocols_used.join(', ')}
              </Tag>
            )}
          </div>

          {/* Validation Status */}
          {validationResult.is_valid ? (
            <Alert
              message="Scenario has warnings but can be deployed"
              description="Review the warnings below. You can proceed with deployment, but the generated traffic may not be optimal."
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
          ) : (
            <Alert
              message="Scenario has errors and cannot be deployed"
              description="Please fix the errors below before deploying."
              type="error"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          {/* Warnings/Errors List */}
          <div
            style={{
              maxHeight: 300,
              overflowY: 'auto',
              background: '#1a2734',
              borderRadius: 4,
              padding: 12,
            }}
          >
            {validationResult.warnings.map((warning, index) => (
              <div
                key={index}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                  padding: '8px 0',
                  borderBottom:
                    index < validationResult.warnings.length - 1
                      ? '1px solid #2a3f54'
                      : 'none',
                }}
              >
                {warning.severity === 'error' ? (
                  <CloseCircleOutlined
                    style={{ color: '#ff4d4f', marginTop: 2 }}
                  />
                ) : (
                  <ExclamationCircleOutlined
                    style={{ color: '#faad14', marginTop: 2 }}
                  />
                )}
                <div>
                  <Text style={{ color: '#e6f1ff', fontSize: 13 }}>
                    {warning.message}
                  </Text>
                  {warning.details && (
                    <div>
                      <Text
                        style={{
                          color: '#6a8caf',
                          fontSize: 11,
                        }}
                      >
                        {warning.details}
                      </Text>
                    </div>
                  )}
                  <Tag
                    style={{ marginTop: 4, fontSize: 10 }}
                    color={
                      warning.severity === 'error'
                        ? 'error'
                        : 'warning'
                    }
                  >
                    {warning.code}
                  </Tag>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Modal>
  );
});

ValidationModal.displayName = 'ValidationModal';

export default ValidationModal;
