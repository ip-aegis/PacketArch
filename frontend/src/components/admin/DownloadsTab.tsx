/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Downloads tab for admin settings page
 * Allows users to download documentation and resources
 */

import React, { useEffect, useState } from 'react';
import {
  Card,
  Button,
  Space,
  Alert,
  Typography,
  Spin,
  Table,
  Tag,
  Empty,
} from 'antd';
import {
  DownloadOutlined,
  FileTextOutlined,
  FilePdfOutlined,
  FileMarkdownOutlined,
  FolderOpenOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { downloadsApi, DownloadableFile } from '../../api/downloads';

const { Text, Title } = Typography;

const DownloadsTab: React.FC = () => {
  const [files, setFiles] = useState<DownloadableFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadingFile, setDownloadingFile] = useState<string | null>(null);

  const fetchFiles = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await downloadsApi.list();
      setFiles(response.files);
    } catch (err: any) {
      setError(err.message || 'Failed to load downloads');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const handleDownload = async (filename: string) => {
    setDownloadingFile(filename);
    try {
      await downloadsApi.downloadFile(filename);
    } catch (err: any) {
      setError(err.message || 'Failed to download file');
    } finally {
      setDownloadingFile(null);
    }
  };

  const getFileIcon = (filename: string) => {
    if (filename.endsWith('.pdf')) {
      return <FilePdfOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />;
    }
    if (filename.endsWith('.md')) {
      return <FileMarkdownOutlined style={{ color: '#1890ff', fontSize: 20 }} />;
    }
    return <FileTextOutlined style={{ color: '#52c41a', fontSize: 20 }} />;
  };

  const getCategoryTag = (category: string) => {
    const categoryColors: Record<string, string> = {
      documentation: 'blue',
      template: 'green',
      tool: 'purple',
    };
    return <Tag color={categoryColors[category] || 'default'}>{category}</Tag>;
  };

  const columns: ColumnsType<DownloadableFile> = [
    {
      title: '',
      key: 'icon',
      width: 50,
      render: (_, record) => getFileIcon(record.filename),
    },
    {
      title: 'Name',
      key: 'name',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.filename}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      render: (text) => <Text type="secondary">{text}</Text>,
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category) => getCategoryTag(category),
    },
    {
      title: 'Size',
      dataIndex: 'size_human',
      key: 'size',
      width: 100,
      render: (size) => <Text type="secondary">{size}</Text>,
    },
    {
      title: 'Action',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Button
          type="primary"
          icon={<DownloadOutlined />}
          loading={downloadingFile === record.filename}
          onClick={() => handleDownload(record.filename)}
        >
          Download
        </Button>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">Loading available downloads...</Text>
        </div>
      </div>
    );
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {error && (
        <Alert
          message="Error"
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
        />
      )}

      <Card
        title={
          <Space>
            <FolderOpenOutlined />
            <span>Available Downloads</span>
          </Space>
        }
        size="small"
        extra={
          <Button onClick={fetchFiles} loading={isLoading}>
            Refresh
          </Button>
        }
      >
        {files.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Space direction="vertical">
                <Text type="secondary">No downloads available</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Check back later for documentation and resources
                </Text>
              </Space>
            }
          />
        ) : (
          <Table
            columns={columns}
            dataSource={files}
            rowKey="filename"
            pagination={false}
            size="middle"
          />
        )}
      </Card>

      <Card title="About Downloads" size="small">
        <Text type="secondary">
          This section provides downloadable documentation and resources for PacketArch:
        </Text>
        <ul style={{ marginTop: 8 }}>
          <li>
            <Text strong>Briefing Deck (PDF)</Text> - Comprehensive slide presentation covering
            PacketArch architecture, features, and capabilities
          </li>
          <li>
            <Text strong>Marp Source (MD)</Text> - Editable markdown source for the briefing
            deck - customize and re-export using{' '}
            <a href="https://marp.app" target="_blank" rel="noopener noreferrer">
              Marp
            </a>
          </li>
        </ul>
      </Card>
    </Space>
  );
};

export default DownloadsTab;
