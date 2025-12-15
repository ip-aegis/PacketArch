/**
 * PCAP Upload Panel - Upload and manage PCAP captures for learning
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Upload,
  Card,
  Space,
  Typography,
  Progress,
  Tag,
  Button,
  Select,
  Input,
  List,
  Empty,
  Spin,
  Modal,
  message,
  Tooltip,
} from 'antd';
import {
  InboxOutlined,
  FileOutlined,
  DeleteOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';
import {
  uploadPcap,
  listPcapCaptures,
  deletePcapCapture,
  getPcapCapture,
  retryPcapProcessing,
  type PcapCapture,
} from '../../api/learning';

const { Dragger } = Upload;
const { Text, Title } = Typography;
const { TextArea } = Input;

interface PcapUploadPanelProps {
  onPcapProcessed?: (captureId: string) => void;
  suggestedProtocol?: string;
  suggestedVertical?: string;
}

const statusConfig: Record<
  string,
  { color: string; icon: React.ReactNode; label: string }
> = {
  pending: {
    color: 'default',
    icon: <ClockCircleOutlined />,
    label: 'Pending',
  },
  processing: {
    color: 'processing',
    icon: <LoadingOutlined spin />,
    label: 'Processing',
  },
  completed: {
    color: 'success',
    icon: <CheckCircleOutlined />,
    label: 'Completed',
  },
  failed: {
    color: 'error',
    icon: <CloseCircleOutlined />,
    label: 'Failed',
  },
};

const PcapUploadPanel: React.FC<PcapUploadPanelProps> = ({
  onPcapProcessed,
  suggestedProtocol,
  suggestedVertical,
}) => {
  const [captures, setCaptures] = useState<PcapCapture[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [description, setDescription] = useState('');
  const [sourceEnvironment, setSourceEnvironment] = useState('');
  const [industryVertical, setIndustryVertical] = useState(suggestedVertical || '');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [pollingIds, setPollingIds] = useState<Set<string>>(new Set());

  // Fetch captures on mount
  const fetchCaptures = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listPcapCaptures({ page_size: 50 });
      setCaptures(data.captures);

      // Track which captures are still processing
      const processingIds = new Set(
        data.captures
          .filter((c) => c.status === 'pending' || c.status === 'processing')
          .map((c) => c.id)
      );
      setPollingIds(processingIds);
    } catch (err) {
      console.error('Failed to fetch captures:', err);
      message.error('Failed to load PCAP captures');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCaptures();
  }, [fetchCaptures]);

  // Poll for processing status updates
  useEffect(() => {
    if (pollingIds.size === 0) return;

    const interval = setInterval(async () => {
      for (const id of pollingIds) {
        try {
          const capture = await getPcapCapture(id);
          if (capture.status === 'completed' || capture.status === 'failed') {
            setPollingIds((prev) => {
              const next = new Set(prev);
              next.delete(id);
              return next;
            });
            setCaptures((prev) =>
              prev.map((c) => (c.id === id ? capture : c))
            );
            if (capture.status === 'completed') {
              message.success(`PCAP "${capture.original_filename}" processed successfully`);
              onPcapProcessed?.(id);
            } else if (capture.status === 'failed') {
              message.error(`PCAP processing failed: ${capture.error_message}`);
            }
          } else {
            setCaptures((prev) =>
              prev.map((c) => (c.id === id ? capture : c))
            );
          }
        } catch (err) {
          console.error(`Failed to poll capture ${id}:`, err);
        }
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [pollingIds, onPcapProcessed]);

  // Handle file selection
  const handleFileSelect: UploadProps['beforeUpload'] = (file) => {
    const isValidType = file.name.endsWith('.pcap') ||
                        file.name.endsWith('.pcapng') ||
                        file.name.endsWith('.cap');
    if (!isValidType) {
      message.error('Only .pcap, .pcapng, and .cap files are allowed');
      return false;
    }
    setSelectedFile(file);
    setUploadModalVisible(true);
    return false; // Prevent auto upload
  };

  // Handle upload
  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    try {
      const result = await uploadPcap(selectedFile, {
        description: description || undefined,
        source_environment: sourceEnvironment || undefined,
        industry_vertical: industryVertical || undefined,
      });

      message.success('PCAP uploaded successfully');
      setUploadModalVisible(false);
      setSelectedFile(null);
      setDescription('');
      setSourceEnvironment('');

      // Add to polling
      setPollingIds((prev) => new Set(prev).add(result.id));

      // Refresh list
      await fetchCaptures();
    } catch (err: any) {
      console.error('Failed to upload PCAP:', err);
      if (err?.response?.status === 409) {
        message.warning('This PCAP file has already been uploaded');
      } else {
        message.error('Failed to upload PCAP');
      }
    } finally {
      setUploading(false);
    }
  };

  // Handle delete
  const handleDelete = async (captureId: string) => {
    Modal.confirm({
      title: 'Delete PCAP Capture',
      content: 'Are you sure you want to delete this capture and all learned patterns?',
      okText: 'Delete',
      okType: 'danger',
      onOk: async () => {
        try {
          await deletePcapCapture(captureId);
          message.success('PCAP capture deleted');
          setCaptures((prev) => prev.filter((c) => c.id !== captureId));
        } catch (err) {
          console.error('Failed to delete capture:', err);
          message.error('Failed to delete capture');
        }
      },
    });
  };

  // Handle retry
  const handleRetry = async (captureId: string) => {
    try {
      await retryPcapProcessing(captureId);
      message.success('Processing restarted');
      // Add to polling
      setPollingIds((prev) => new Set(prev).add(captureId));
      // Update status in list
      setCaptures((prev) =>
        prev.map((c) =>
          c.id === captureId ? { ...c, status: 'pending' as const, error_message: null } : c
        )
      );
    } catch (err) {
      console.error('Failed to retry processing:', err);
      message.error('Failed to retry processing');
    }
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Upload Area */}
      <Card
        size="small"
        title={
          <Space>
            <InboxOutlined />
            <span>Upload PCAP</span>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '12px' } }}
      >
        <Dragger
          accept=".pcap,.pcapng,.cap"
          showUploadList={false}
          beforeUpload={handleFileSelect}
          style={{ background: '#0d1117', borderColor: '#2a3f54' }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined style={{ color: '#5a9fd4', fontSize: 32 }} />
          </p>
          <p style={{ color: '#8aa4bc', fontSize: 12 }}>
            Click or drag PCAP file to upload
          </p>
          <p style={{ color: '#6a8caf', fontSize: 10 }}>
            Supports .pcap, .pcapng, .cap files
          </p>
        </Dragger>

        {suggestedProtocol && (
          <div style={{ marginTop: 8 }}>
            <Text style={{ fontSize: 10, color: '#6a8caf' }}>
              <InfoCircleOutlined /> Suggested: Upload {suggestedProtocol} traffic
            </Text>
          </div>
        )}
      </Card>

      {/* Captures List */}
      <Card
        size="small"
        title={
          <Space>
            <FileOutlined />
            <span>Uploaded Captures</span>
            <Tag>{captures.length}</Tag>
          </Space>
        }
        extra={
          <Button
            type="text"
            size="small"
            icon={<ReloadOutlined />}
            onClick={fetchCaptures}
            loading={loading}
          />
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '8px' } }}
      >
        {loading && captures.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
          </div>
        ) : captures.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Text style={{ color: '#6a8caf', fontSize: 11 }}>
                No PCAP captures yet
              </Text>
            }
          />
        ) : (
          <List
            dataSource={captures}
            size="small"
            renderItem={(capture) => {
              const config = statusConfig[capture.status] || statusConfig.pending;
              return (
                <List.Item
                  style={{
                    padding: '8px',
                    background: '#0d1117',
                    borderRadius: 4,
                    marginBottom: 4,
                  }}
                  actions={[
                    capture.status !== 'completed' && (
                      <Tooltip key="retry" title="Retry processing">
                        <Button
                          type="text"
                          size="small"
                          icon={<ReloadOutlined />}
                          onClick={() => handleRetry(capture.id)}
                          disabled={capture.status === 'processing'}
                        />
                      </Tooltip>
                    ),
                    <Tooltip key="delete" title="Delete">
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleDelete(capture.id)}
                      />
                    </Tooltip>,
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    title={
                      <Space size={4}>
                        <Text
                          style={{ fontSize: 11, color: '#c9d1d9' }}
                          ellipsis={{ tooltip: capture.original_filename }}
                        >
                          {capture.original_filename}
                        </Text>
                        <Tag
                          color={config.color}
                          icon={config.icon}
                          style={{ fontSize: 9 }}
                        >
                          {config.label}
                        </Tag>
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size={0}>
                        <Text style={{ fontSize: 10, color: '#6a8caf' }}>
                          {formatFileSize(capture.file_size)}
                          {capture.packet_count && ` | ${capture.packet_count.toLocaleString()} packets`}
                          {capture.flow_count && ` | ${capture.flow_count} flows`}
                        </Text>
                        {capture.protocol_stats && (
                          <Space size={4} wrap>
                            {/* Handle nested structure with packet_counts */}
                            {capture.protocol_stats.packet_counts
                              ? Object.entries(capture.protocol_stats.packet_counts as Record<string, number>)
                                  .filter(([proto]) => proto !== 'unknown')
                                  .map(([proto, count]) => (
                                    <Tag key={proto} style={{ fontSize: 9 }}>
                                      {proto}: {(count as number).toLocaleString()}
                                    </Tag>
                                  ))
                              : Object.entries(capture.protocol_stats)
                                  .filter(([key]) => typeof capture.protocol_stats![key] === 'number')
                                  .map(([proto, count]) => (
                                    <Tag key={proto} style={{ fontSize: 9 }}>
                                      {proto}: {(count as number).toLocaleString()}
                                    </Tag>
                                  ))}
                          </Space>
                        )}
                        {capture.error_message && (
                          <Text type="danger" style={{ fontSize: 10 }}>
                            {capture.error_message}
                          </Text>
                        )}
                      </Space>
                    }
                  />
                </List.Item>
              );
            }}
          />
        )}
      </Card>

      {/* Upload Modal */}
      <Modal
        title="Upload PCAP"
        open={uploadModalVisible}
        onCancel={() => {
          setUploadModalVisible(false);
          setSelectedFile(null);
        }}
        footer={[
          <Button key="cancel" onClick={() => setUploadModalVisible(false)}>
            Cancel
          </Button>,
          <Button
            key="upload"
            type="primary"
            loading={uploading}
            onClick={handleUpload}
          >
            Upload
          </Button>,
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>
              Selected File
            </Text>
            <Tag icon={<FileOutlined />}>
              {selectedFile?.name}
            </Tag>
          </div>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>
              Description (optional)
            </Text>
            <TextArea
              rows={2}
              placeholder="Describe the traffic capture..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>
              Source Environment (optional)
            </Text>
            <Input
              placeholder="e.g., Lab, Production, Simulation"
              value={sourceEnvironment}
              onChange={(e) => setSourceEnvironment(e.target.value)}
            />
          </div>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>
              Industry Vertical (optional)
            </Text>
            <Select
              style={{ width: '100%' }}
              placeholder="Select vertical"
              value={industryVertical || undefined}
              onChange={setIndustryVertical}
              allowClear
              options={[
                { value: 'manufacturing', label: 'Manufacturing' },
                { value: 'water', label: 'Water/Wastewater' },
                { value: 'energy', label: 'Energy/Power' },
                { value: 'oil_gas', label: 'Oil & Gas' },
              ]}
            />
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default PcapUploadPanel;
