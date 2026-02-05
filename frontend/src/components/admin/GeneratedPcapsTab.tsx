/**
 * Generated PCAPs tab for Settings page
 * Displays a list of all PCAP generation jobs with download/delete actions
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Empty,
  message,
  Popconfirm,
  Select,
  Progress,
  Tooltip,
} from 'antd';
import {
  DownloadOutlined,
  DeleteOutlined,
  ReloadOutlined,
  CloseCircleOutlined,
  FileOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  ExclamationCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { generationApi, type GenerationJob } from '../../api/generation';
import { formatRelativeTime } from '../../utils/dateUtils';
import { Link } from 'react-router-dom';

const { Text } = Typography;

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`;
  return `${(ms / 3600000).toFixed(1)}h`;
};

const statusConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  pending: { color: 'default', icon: <ClockCircleOutlined />, label: 'Pending' },
  running: { color: 'processing', icon: <LoadingOutlined spin />, label: 'Running' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, label: 'Completed' },
  failed: { color: 'error', icon: <ExclamationCircleOutlined />, label: 'Failed' },
  cancelled: { color: 'warning', icon: <StopOutlined />, label: 'Cancelled' },
};

const GeneratedPcapsTab: React.FC = () => {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Fetch jobs
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['generation-jobs', statusFilter],
    queryFn: () => generationApi.listJobs({ status: statusFilter, limit: 100 }),
    refetchInterval: autoRefresh ? 3000 : false,
  });

  // Check if there are any running/pending jobs
  const hasActiveJobs = data?.jobs.some(
    (job) => job.status === 'pending' || job.status === 'running'
  );

  // Only auto-refresh if there are active jobs
  useEffect(() => {
    setAutoRefresh(hasActiveJobs ?? false);
  }, [hasActiveJobs]);

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: (jobId: string) => generationApi.cancelJob(jobId),
    onSuccess: () => {
      message.success('Job cancelled');
      queryClient.invalidateQueries({ queryKey: ['generation-jobs'] });
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail || 'Failed to cancel job';
      message.error(detail);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (jobId: string) => generationApi.deleteJob(jobId),
    onSuccess: () => {
      message.success('Job deleted');
      queryClient.invalidateQueries({ queryKey: ['generation-jobs'] });
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail || 'Failed to delete job';
      message.error(detail);
    },
  });

  // Download handler
  const handleDownload = useCallback(async (job: GenerationJob) => {
    try {
      const filename = job.output_path
        ? job.output_path.split('/').pop()
        : `pcap_${job.job_id.substring(0, 8)}.pcap`;
      await generationApi.downloadPcap(job.job_id, filename);
      message.success('Download started');
    } catch (error: any) {
      const detail = error.response?.data?.detail || 'Failed to download PCAP';
      message.error(detail);
    }
  }, []);

  const columns = [
    {
      title: 'Scenario',
      dataIndex: 'scenario_name',
      key: 'scenario_name',
      render: (name: string | undefined, record: GenerationJob) => (
        <Link to={`/studio?scenario=${record.scenario_id}`} style={{ color: '#1890ff' }}>
          {name || 'Unknown Scenario'}
        </Link>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (status: string, record: GenerationJob) => {
        const config = statusConfig[status] || statusConfig.pending;
        return (
          <Space direction="vertical" size={4}>
            <Tag color={config.color} icon={config.icon}>
              {config.label}
            </Tag>
            {status === 'running' && (
              <Progress
                percent={Math.round(record.progress)}
                size="small"
                style={{ width: 100 }}
                status="active"
              />
            )}
            {status === 'failed' && record.error_message && (
              <Tooltip title={record.error_message}>
                <Text type="danger" style={{ fontSize: 11 }} ellipsis>
                  {record.error_message.substring(0, 30)}...
                </Text>
              </Tooltip>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Duration',
      dataIndex: 'total_duration_ms',
      key: 'duration',
      width: 100,
      render: (ms: number) => formatDuration(ms),
    },
    {
      title: 'Packets',
      dataIndex: 'packets_generated',
      key: 'packets',
      width: 100,
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: 'File Size',
      dataIndex: 'file_size_bytes',
      key: 'size',
      width: 100,
      render: (bytes: number) => formatFileSize(bytes),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created',
      width: 150,
      render: (date: string | undefined) =>
        date ? formatRelativeTime(date) : '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_: any, record: GenerationJob) => (
        <Space>
          {record.status === 'completed' && (
            <Tooltip title="Download PCAP">
              <Button
                type="primary"
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => handleDownload(record)}
              />
            </Tooltip>
          )}
          {(record.status === 'pending' || record.status === 'running') && (
            <Tooltip title="Cancel">
              <Button
                size="small"
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => cancelMutation.mutate(record.job_id)}
                loading={cancelMutation.isPending}
              />
            </Tooltip>
          )}
          {(record.status === 'completed' ||
            record.status === 'failed' ||
            record.status === 'cancelled') && (
            <Popconfirm
              title="Delete this job?"
              description="This will also delete the PCAP file if it exists."
              onConfirm={() => deleteMutation.mutate(record.job_id)}
              okText="Delete"
              okButtonProps={{ danger: true }}
            >
              <Tooltip title="Delete">
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  loading={deleteMutation.isPending}
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {/* Filters and actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Select
            placeholder="Filter by status"
            allowClear
            value={statusFilter}
            onChange={setStatusFilter}
            style={{ width: 150 }}
            options={[
              { value: 'pending', label: 'Pending' },
              { value: 'running', label: 'Running' },
              { value: 'completed', label: 'Completed' },
              { value: 'failed', label: 'Failed' },
              { value: 'cancelled', label: 'Cancelled' },
            ]}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {data?.total || 0} total jobs
          </Text>
        </Space>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
          Refresh
        </Button>
      </div>

      {/* Jobs table */}
      <Table
        dataSource={data?.jobs || []}
        columns={columns}
        rowKey="job_id"
        loading={isLoading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total) => `${total} jobs`,
        }}
        locale={{
          emptyText: (
            <Empty
              image={<FileOutlined style={{ fontSize: 48, color: '#2d2d52' }} />}
              description={
                <Text style={{ color: '#6b6b8a' }}>
                  No PCAP generation jobs yet. Generate a PCAP from the Scenarios page.
                </Text>
              }
            />
          ),
        }}
        style={{
          background: '#141428',
          borderRadius: 8,
        }}
      />
    </Space>
  );
};

export default GeneratedPcapsTab;
