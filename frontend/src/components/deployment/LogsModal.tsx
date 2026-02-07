/**
 * LogsModal - Deployment container logs viewer.
 */

import React from 'react';
import { Button, Modal, Space, Spin } from 'antd';
import { FileTextOutlined, ReloadOutlined } from '@ant-design/icons';

export interface DeploymentLogs {
  container_id: string;
  logs: string;
}

export interface LogsModalProps {
  open: boolean;
  logs: DeploymentLogs | null;
  onClose: () => void;
  onRefresh: () => void;
}

const LogsModal: React.FC<LogsModalProps> = React.memo(({
  open,
  logs,
  onClose,
  onRefresh,
}) => {
  return (
    <Modal
      title={
        <Space>
          <FileTextOutlined />
          Container Logs
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={onRefresh}>
            Refresh
          </Button>
          <Button onClick={onClose}>Close</Button>
        </Space>
      }
      width={700}
    >
      {logs ? (
        <pre
          style={{
            background: '#0d1117',
            padding: 12,
            borderRadius: 4,
            maxHeight: 400,
            overflow: 'auto',
            fontSize: 11,
            fontFamily: 'monospace',
            color: '#c9d1d9',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}
        >
          {logs.logs || 'No logs available'}
        </pre>
      ) : (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <Spin />
        </div>
      )}
    </Modal>
  );
});

LogsModal.displayName = 'LogsModal';

export default LogsModal;
