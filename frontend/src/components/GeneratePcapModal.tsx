/**
 * Modal for generating PCAP files from scenarios
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  Form,
  InputNumber,
  Button,
  Progress,
  Space,
  Typography,
  Statistic,
  Row,
  Col,
  Alert,
  message,
} from 'antd';
import {
  FileOutlined,
  DownloadOutlined,
  CloseCircleOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { generationApi, type GenerationJob } from '../api/generation';
import { extractErrorMessage } from '../utils/errorUtils';

const { Text, Title } = Typography;

interface GeneratePcapModalProps {
  open: boolean;
  onClose: () => void;
  scenarioId: string;
  scenarioName: string;
  defaultDurationMs: number;
}

const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`;
  return `${(ms / 3600000).toFixed(1)}h`;
};

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

const GeneratePcapModal: React.FC<GeneratePcapModalProps> = ({
  open,
  onClose,
  scenarioId,
  scenarioName,
  defaultDurationMs,
}) => {
  const [form] = Form.useForm();
  const [job, setJob] = useState<GenerationJob | null>(null);
  const [polling, setPolling] = useState(false);

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setJob(null);
      setPolling(false);
      form.setFieldsValue({ duration_ms: defaultDurationMs });
    }
  }, [open, defaultDurationMs, form]);

  // Poll for job status
  useEffect(() => {
    if (!polling || !job) return;

    const interval = setInterval(async () => {
      try {
        const updatedJob = await generationApi.getJobStatus(job.job_id);
        setJob(updatedJob);

        // Stop polling when job is complete
        if (['completed', 'failed', 'cancelled'].includes(updatedJob.status)) {
          setPolling(false);
        }
      } catch (error) {
        console.error('Failed to poll job status:', error);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [polling, job]);

  // Start generation mutation
  const startMutation = useMutation({
    mutationFn: (durationMs: number) =>
      generationApi.startGeneration({
        scenario_id: scenarioId,
        duration_override_ms: durationMs,
      }),
    onSuccess: (newJob) => {
      setJob(newJob);
      setPolling(true);
    },
    onError: (error: unknown) => {
      const detail = extractErrorMessage(error, 'Failed to start generation');
      message.error(detail);
    },
  });

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: () => generationApi.cancelJob(job!.job_id),
    onSuccess: () => {
      message.info('Generation cancelled');
      setPolling(false);
      if (job) {
        setJob({ ...job, status: 'cancelled' });
      }
    },
    onError: (error: unknown) => {
      const detail = extractErrorMessage(error, 'Failed to cancel');
      message.error(detail);
    },
  });

  // Download handler
  const handleDownload = useCallback(async () => {
    if (!job) return;
    try {
      const filename = job.output_path
        ? job.output_path.split('/').pop()
        : `${scenarioName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.pcap`;
      await generationApi.downloadPcap(job.job_id, filename);
      message.success('Download started');
    } catch (error: unknown) {
      const detail = extractErrorMessage(error, 'Failed to download');
      message.error(detail);
    }
  }, [job, scenarioName]);

  const handleStart = () => {
    form.validateFields().then((values) => {
      startMutation.mutate(values.duration_ms);
    });
  };

  const handleClose = () => {
    if (job && (job.status === 'pending' || job.status === 'running')) {
      // Ask for confirmation before closing
      Modal.confirm({
        title: 'Cancel generation?',
        content: 'Closing will cancel the current generation job.',
        okText: 'Yes, cancel',
        cancelText: 'No, keep running',
        onOk: () => {
          cancelMutation.mutate();
          onClose();
        },
      });
    } else {
      onClose();
    }
  };

  const isRunning = job && (job.status === 'pending' || job.status === 'running');
  const isComplete = job?.status === 'completed';
  const isFailed = job?.status === 'failed';
  const isCancelled = job?.status === 'cancelled';

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: 'linear-gradient(135deg, #049FD920 0%, #049FD910 100%)',
              border: '1px solid #049FD940',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#049FD9',
            }}
          >
            <FileOutlined style={{ fontSize: 18 }} />
          </div>
          <span style={{ color: '#fff', fontSize: 16 }}>Generate PCAP</span>
        </div>
      }
      open={open}
      onCancel={handleClose}
      footer={null}
      width={500}
      styles={{
        header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
        body: { background: '#1a1a2e', padding: 24 },
        content: { background: '#141428' },
      }}
    >
      {/* Scenario info */}
      <div
        style={{
          background: '#141428',
          borderRadius: 8,
          padding: 16,
          marginBottom: 24,
          border: '1px solid #2d2d52',
        }}
      >
        <Text style={{ color: '#6b6b8a', fontSize: 12 }}>Scenario</Text>
        <Title level={5} style={{ color: '#fff', margin: '4px 0 0 0' }}>
          {scenarioName}
        </Title>
      </div>

      {/* Pre-generation form */}
      {!job && (
        <Form form={form} layout="vertical" onFinish={handleStart}>
          <Form.Item
            name="duration_ms"
            label={<Text style={{ color: '#a8a8c0' }}>Duration (milliseconds)</Text>}
            rules={[
              { required: true, message: 'Please enter a duration' },
              { type: 'number', min: 1000, message: 'Minimum duration is 1000ms' },
              { type: 'number', max: 600000, message: 'Maximum duration is 600000ms (10 minutes)' },
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={1000}
              max={600000}
              step={1000}
              addonAfter={
                <Text style={{ color: '#6b6b8a' }}>
                  = {formatDuration(form.getFieldValue('duration_ms') || defaultDurationMs)}
                </Text>
              }
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={onClose}>Cancel</Button>
              <Button
                type="primary"
                htmlType="submit"
                loading={startMutation.isPending}
                icon={<FileOutlined />}
              >
                Generate PCAP
              </Button>
            </Space>
          </Form.Item>
        </Form>
      )}

      {/* Generation progress */}
      {job && (
        <>
          {/* Status indicator */}
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            {isRunning && (
              <>
                <LoadingOutlined style={{ fontSize: 48, color: '#1890ff', marginBottom: 16 }} />
                <div>
                  <Text style={{ color: '#fff', fontSize: 16 }}>Generating traffic...</Text>
                </div>
                <Progress
                  percent={Math.round(job.progress)}
                  status="active"
                  style={{ marginTop: 16 }}
                />
              </>
            )}
            {isComplete && (
              <>
                <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a', marginBottom: 16 }} />
                <div>
                  <Text style={{ color: '#52c41a', fontSize: 16 }}>Generation complete!</Text>
                </div>
              </>
            )}
            {isFailed && (
              <>
                <CloseCircleOutlined style={{ fontSize: 48, color: '#ff4d4f', marginBottom: 16 }} />
                <div>
                  <Text style={{ color: '#ff4d4f', fontSize: 16 }}>Generation failed</Text>
                </div>
                {job.error_message && (
                  <Alert
                    message={job.error_message}
                    type="error"
                    style={{ marginTop: 16, textAlign: 'left' }}
                  />
                )}
              </>
            )}
            {isCancelled && (
              <>
                <CloseCircleOutlined style={{ fontSize: 48, color: '#faad14', marginBottom: 16 }} />
                <div>
                  <Text style={{ color: '#faad14', fontSize: 16 }}>Generation cancelled</Text>
                </div>
              </>
            )}
          </div>

          {/* Stats */}
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={8}>
              <Statistic
                title={<Text style={{ color: '#6b6b8a' }}>Packets</Text>}
                value={job.packets_generated}
                valueStyle={{ color: '#fff', fontSize: 20 }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title={<Text style={{ color: '#6b6b8a' }}>File Size</Text>}
                value={formatFileSize(job.file_size_bytes)}
                valueStyle={{ color: '#fff', fontSize: 20 }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title={<Text style={{ color: '#6b6b8a' }}>Duration</Text>}
                value={formatDuration(job.total_duration_ms)}
                valueStyle={{ color: '#fff', fontSize: 20 }}
              />
            </Col>
          </Row>

          {/* Action buttons */}
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            {isRunning && (
              <Button
                danger
                onClick={() => cancelMutation.mutate()}
                loading={cancelMutation.isPending}
                icon={<CloseCircleOutlined />}
              >
                Cancel
              </Button>
            )}
            {isComplete && (
              <>
                <Button onClick={onClose}>Close</Button>
                <Button type="primary" icon={<DownloadOutlined />} onClick={handleDownload}>
                  Download PCAP
                </Button>
              </>
            )}
            {(isFailed || isCancelled) && (
              <>
                <Button onClick={onClose}>Close</Button>
                <Button
                  type="primary"
                  onClick={() => {
                    setJob(null);
                    form.setFieldsValue({ duration_ms: defaultDurationMs });
                  }}
                >
                  Try Again
                </Button>
              </>
            )}
          </Space>
        </>
      )}
    </Modal>
  );
};

export default GeneratePcapModal;
