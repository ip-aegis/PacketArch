/**
 * AgentUpdateCard - Modal for tracking agent update progress via steps.
 */

import React from 'react';
import {
  Button,
  Card,
  Modal,
  Progress,
  Result,
  Space,
  Steps,
  Tag,
  Typography,
} from 'antd';
import {
  CloudUploadOutlined,
  DownloadOutlined,
  LoadingOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { AgentUpdateStatus } from '../../types/agent';

const { Text } = Typography;

export interface AgentUpdateCardProps {
  open: boolean;
  updateStatus: AgentUpdateStatus | null;
  onClose: () => void;
}

/** Map update status string to step index */
const getUpdateStepIndex = (status: string): number => {
  switch (status) {
    case 'initiated':
      return 0;
    case 'downloading':
      return 1;
    case 'loading':
      return 2;
    case 'restarting':
      return 3;
    case 'complete':
      return 4;
    case 'failed':
    case 'timeout':
      return -1;
    default:
      return 0;
  }
};

const getUpdateStepStatus = (
  stepIndex: number,
  currentIndex: number,
  hasError: boolean,
): 'wait' | 'process' | 'finish' | 'error' => {
  if (hasError) return currentIndex === stepIndex ? 'error' : 'wait';
  if (stepIndex < currentIndex) return 'finish';
  if (stepIndex === currentIndex) return 'process';
  return 'wait';
};

const TERMINAL_STATES = ['complete', 'failed', 'timeout', 'error'];

const AgentUpdateCard: React.FC<AgentUpdateCardProps> = React.memo(({
  open,
  updateStatus,
  onClose,
}) => {
  const isTerminal =
    updateStatus && TERMINAL_STATES.includes(updateStatus.status);

  return (
    <Modal
      title={
        <Space>
          <CloudUploadOutlined />
          Agent Update
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={
        isTerminal ? (
          <Button type="primary" onClick={onClose}>
            Close
          </Button>
        ) : (
          <Text type="secondary">
            Please wait while the agent updates...
          </Text>
        )
      }
      closable={updateStatus ? TERMINAL_STATES.includes(updateStatus.status) : true}
      maskClosable={false}
      width={500}
    >
      {updateStatus && (
        <Space
          direction="vertical"
          size="large"
          style={{ width: '100%' }}
        >
          {/* Terminal: success */}
          {updateStatus.status === 'complete' && (
            <Result
              status="success"
              title="Update Complete"
              subTitle={updateStatus.message}
              extra={
                updateStatus.target_version && (
                  <Tag color="success">
                    v{updateStatus.target_version}
                  </Tag>
                )
              }
            />
          )}

          {/* Terminal: error */}
          {['failed', 'timeout', 'error'].includes(
            updateStatus.status,
          ) && (
            <Result
              status="error"
              title="Update Failed"
              subTitle={updateStatus.error || updateStatus.message}
            />
          )}

          {/* In-progress steps */}
          {!TERMINAL_STATES.includes(updateStatus.status) && (
            <>
              <Steps
                direction="vertical"
                size="small"
                current={getUpdateStepIndex(updateStatus.status)}
                items={[
                  {
                    title: 'Initiating Update',
                    description: 'Sending update command to agent',
                    icon:
                      updateStatus.status === 'initiated' ? (
                        <LoadingOutlined />
                      ) : undefined,
                    status: getUpdateStepStatus(
                      0,
                      getUpdateStepIndex(updateStatus.status),
                      false,
                    ),
                  },
                  {
                    title: 'Downloading Image',
                    description:
                      updateStatus.progress !== null
                        ? `${updateStatus.progress}% complete`
                        : 'Downloading latest agent image',
                    icon:
                      updateStatus.status === 'downloading' ? (
                        <DownloadOutlined />
                      ) : undefined,
                    status: getUpdateStepStatus(
                      1,
                      getUpdateStepIndex(updateStatus.status),
                      false,
                    ),
                  },
                  {
                    title: 'Loading Image',
                    description: 'Loading new Docker image',
                    icon:
                      updateStatus.status === 'loading' ? (
                        <LoadingOutlined />
                      ) : undefined,
                    status: getUpdateStepStatus(
                      2,
                      getUpdateStepIndex(updateStatus.status),
                      false,
                    ),
                  },
                  {
                    title: 'Restarting Agent',
                    description:
                      'Agent is restarting with new version',
                    icon:
                      updateStatus.status === 'restarting' ? (
                        <SyncOutlined spin />
                      ) : undefined,
                    status: getUpdateStepStatus(
                      3,
                      getUpdateStepIndex(updateStatus.status),
                      false,
                    ),
                  },
                ]}
              />

              {/* Download progress bar */}
              {updateStatus.status === 'downloading' &&
                updateStatus.progress !== null && (
                  <Progress
                    percent={updateStatus.progress}
                    status="active"
                    strokeColor={{
                      '0%': '#108ee9',
                      '100%': '#87d068',
                    }}
                  />
                )}

              {/* Current status message */}
              <Card size="small">
                <Text type="secondary">{updateStatus.message}</Text>
              </Card>

              {/* Target version */}
              {updateStatus.target_version && (
                <Text type="secondary">
                  Target version:{' '}
                  <Text code>v{updateStatus.target_version}</Text>
                </Text>
              )}
            </>
          )}
        </Space>
      )}
    </Modal>
  );
});

AgentUpdateCard.displayName = 'AgentUpdateCard';

export default AgentUpdateCard;
