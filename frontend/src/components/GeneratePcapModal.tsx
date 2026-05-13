/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
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
  Collapse,
  Select,
  Slider,
  Switch,
  message,
} from 'antd';
import {
  FileOutlined,
  DownloadOutlined,
  CloseCircleOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ThunderboltOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import { generationApi, type GenerationJob } from '../api/generation';
import { attacksApi } from '../api/attacks';
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
      form.setFieldsValue({
        duration_minutes: Math.round((defaultDurationMs / 60000) * 10) / 10,
        attack_playbook_id: undefined,
        attack_intensity: 1.0,
        adaptive_enabled: false,
        cell_isolation_mode: 'inherit',
      });
    }
  }, [open, defaultDurationMs, form]);

  // Load playbooks for the optional attack section. Open in PCAP-only too.
  const { data: playbooks } = useQuery({
    queryKey: ['attacks', 'playbooks'],
    queryFn: () => attacksApi.listPlaybooks(),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  });

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
    mutationFn: (params: {
      durationMinutes: number;
      attackPlaybookId?: string;
      attackIntensity?: number;
      adaptiveEnabled?: boolean;
      cellIsolationMode?: 'inherit' | 'off' | 'conduit_gated' | 'strict_northbound';
    }) =>
      generationApi.startGeneration({
        scenario_id: scenarioId,
        duration_override_ms: Math.round(params.durationMinutes * 60000),
        attack_playbook_id: params.attackPlaybookId || null,
        attack_config: params.attackPlaybookId
          ? { intensity: params.attackIntensity ?? 1.0 }
          : null,
        adaptive_config: params.adaptiveEnabled ? { enabled: true } : null,
        cell_isolation_override:
          params.cellIsolationMode && params.cellIsolationMode !== 'inherit'
            ? { mode: params.cellIsolationMode }
            : null,
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
      startMutation.mutate({
        durationMinutes: values.duration_minutes,
        attackPlaybookId: values.attack_playbook_id,
        attackIntensity: values.attack_intensity,
        adaptiveEnabled: values.adaptive_enabled,
        cellIsolationMode: values.cell_isolation_mode,
      });
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
            name="duration_minutes"
            label={<Text style={{ color: '#a8a8c0' }}>Duration (minutes)</Text>}
            rules={[
              { required: true, message: 'Please enter a duration' },
              { type: 'number', min: 0.5, message: 'Minimum duration is 0.5 minutes (30 seconds)' },
              { type: 'number', max: 60, message: 'Maximum duration is 60 minutes' },
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0.5}
              max={60}
              step={0.5}
              precision={1}
              addonAfter={
                <Text style={{ color: '#6b6b8a' }}>
                  = {formatDuration((form.getFieldValue('duration_minutes') || defaultDurationMs / 60000) * 60000)}
                </Text>
              }
            />
          </Form.Item>

          <Collapse
            ghost
            size="small"
            style={{ marginBottom: 16 }}
            items={[
              {
                key: 'attack',
                label: (
                  <span style={{ color: '#a8a8c0' }}>
                    <ThunderboltOutlined style={{ marginRight: 8 }} />
                    Attack Playbook (optional)
                  </span>
                ),
                children: (
                  <>
                    <Form.Item
                      name="attack_playbook_id"
                      label={<Text style={{ color: '#a8a8c0' }}>Playbook</Text>}
                    >
                      <Select
                        allowClear
                        placeholder="No attack — generate clean traffic"
                        options={(playbooks ?? []).map((pb) => ({
                          value: pb.playbook_id,
                          label: `${pb.name} (${pb.severity})`,
                        }))}
                      />
                    </Form.Item>
                    <Form.Item
                      name="attack_intensity"
                      label={<Text style={{ color: '#a8a8c0' }}>Intensity (0.1×–3×)</Text>}
                      tooltip="Multiplier applied to per-stage action counts. 1.0 = playbook default."
                    >
                      <Slider min={0.1} max={3.0} step={0.1} />
                    </Form.Item>
                    <Alert
                      type="info"
                      showIcon
                      message="Attack stages are pre-baked into the PCAP at generation time. Live runtime controls (advance, pause, inject) are not available in PCAP mode."
                      style={{ marginTop: 8 }}
                    />
                  </>
                ),
              },
              {
                key: 'adaptive',
                label: (
                  <span style={{ color: '#a8a8c0' }}>
                    <LineChartOutlined style={{ marginRight: 8 }} />
                    Adaptive Traffic (optional)
                  </span>
                ),
                children: (
                  <>
                    <Form.Item
                      name="adaptive_enabled"
                      label={<Text style={{ color: '#a8a8c0' }}>Enable timing drift</Text>}
                      valuePropName="checked"
                      tooltip="Adds bounded random walk to poll intervals (±5%) plus retransmits and connection resets, matching live agent behavior."
                    >
                      <Switch />
                    </Form.Item>
                  </>
                ),
              },
              {
                key: 'cell_isolation',
                label: (
                  <span style={{ color: '#a8a8c0' }}>
                    Cell Isolation (override)
                  </span>
                ),
                children: (
                  <Form.Item
                    name="cell_isolation_mode"
                    label={<Text style={{ color: '#a8a8c0' }}>Mode for this run</Text>}
                    tooltip="Per-run override of the scenario's Purdue-aware cell isolation mode. Inherit uses whatever the scenario was saved with."
                  >
                    <Select
                      options={[
                        { value: 'inherit', label: 'Inherit from scenario' },
                        { value: 'off', label: 'Off — permissive' },
                        { value: 'conduit_gated', label: 'Conduit-gated' },
                        {
                          value: 'strict_northbound',
                          label: 'Strict — no east/west cell traffic',
                        },
                      ]}
                    />
                  </Form.Item>
                ),
              },
            ]}
          />

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
                    form.setFieldsValue({ duration_minutes: Math.round((defaultDurationMs / 60000) * 10) / 10 });
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
