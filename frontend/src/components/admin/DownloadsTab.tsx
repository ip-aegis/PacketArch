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
  FilePptOutlined,
  FolderOpenOutlined,
  CodeOutlined,
  ApiOutlined,
  PlaySquareOutlined,
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
    if (filename.endsWith('.pptx')) {
      return <FilePptOutlined style={{ color: '#d83b01', fontSize: 20 }} />;
    }
    if (filename.endsWith('.md')) {
      return <FileMarkdownOutlined style={{ color: '#1890ff', fontSize: 20 }} />;
    }
    if (filename.endsWith('.json')) {
      return <CodeOutlined style={{ color: '#faad14', fontSize: 20 }} />;
    }
    if (filename.endsWith('.html')) {
      return <FileTextOutlined style={{ color: '#52c41a', fontSize: 20 }} />;
    }
    return <FileTextOutlined style={{ color: '#52c41a', fontSize: 20 }} />;
  };

  const getCategoryTag = (category: string) => {
    const categoryColors: Record<string, string> = {
      presentations: 'magenta',
      documentation: 'blue',
      template: 'green',
      tool: 'purple',
      authoring: 'gold',
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

  const presentationFiles = files.filter((f) => f.category === 'presentations');
  const authoringFiles = files.filter((f) => f.category === 'authoring');
  const otherFiles = files.filter(
    (f) => f.category !== 'presentations' && f.category !== 'authoring',
  );

  // Group presentation files by deck so the table reads
  // "Executive Briefing" once with four format rows instead of eight
  // mixed entries. Deck key = filename without extension.
  const groupedPresentations = (() => {
    const groups: Record<string, DownloadableFile[]> = {};
    for (const f of presentationFiles) {
      const base = f.filename.replace(/\.(pdf|pptx|html|md)$/i, '');
      if (!groups[base]) groups[base] = [];
      groups[base].push(f);
    }
    // Preferred display order: PPTX → PDF → HTML → Marp source
    const formatRank = (filename: string) => {
      if (filename.endsWith('.pptx')) return 0;
      if (filename.endsWith('.pdf')) return 1;
      if (filename.endsWith('.html')) return 2;
      return 3;
    };
    for (const key in groups) {
      groups[key].sort(
        (a, b) => formatRank(a.filename) - formatRank(b.filename),
      );
    }
    // Sort the decks themselves: Executive first, then Technical.
    return Object.entries(groups).sort(([a], [b]) => {
      if (a.includes('Executive')) return -1;
      if (b.includes('Executive')) return 1;
      return a.localeCompare(b);
    });
  })();

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

      {files.length === 0 ? (
        <Card size="small">
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
        </Card>
      ) : (
        <>
          {presentationFiles.length > 0 && (
            <Card
              title={
                <Space>
                  <PlaySquareOutlined />
                  <span>Presentations</span>
                </Space>
              }
              size="small"
              extra={
                <Button onClick={fetchFiles} loading={isLoading} size="small">
                  Refresh
                </Button>
              }
            >
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
                message="Executive briefing and technical deep-dive decks"
                description={
                  <Text>
                    Pre-built slide decks for sharing PacketArch with stakeholders.
                    The <Text strong>Executive Briefing</Text> targets C-suite and
                    security leadership (business value, deployment models,
                    economics). The <Text strong>Technical Deep-Dive</Text> targets
                    security architects and OT engineers (architecture, protocol
                    engines, attack simulation, Cyber Vision integration). Each deck
                    is available as <Text code>.pptx</Text> for editing,{' '}
                    <Text code>.pdf</Text> for distribution, <Text code>.html</Text>
                    {' '}for browser viewing, and Marp <Text code>.md</Text> source
                    for re-export.
                  </Text>
                }
              />
              {groupedPresentations.map(([deckKey, deckFiles]) => {
                const deckTitle = deckKey
                  .replace('PacketArch-', '')
                  .replace(/-/g, ' ');
                return (
                  <div
                    key={deckKey}
                    style={{ marginBottom: 16, paddingBottom: 8 }}
                  >
                    <Title level={5} style={{ marginTop: 0, marginBottom: 8 }}>
                      {deckTitle}
                    </Title>
                    <Table
                      columns={columns}
                      dataSource={deckFiles}
                      rowKey="filename"
                      pagination={false}
                      size="middle"
                      showHeader={false}
                    />
                  </div>
                );
              })}
            </Card>
          )}

          {authoringFiles.length > 0 && (
            <Card
              title={
                <Space>
                  <ApiOutlined />
                  <span>Portable Scenario Authoring Kit</span>
                </Space>
              }
              size="small"
              extra={
                presentationFiles.length === 0 ? (
                  <Button onClick={fetchFiles} loading={isLoading} size="small">
                    Refresh
                  </Button>
                ) : undefined
              }
            >
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
                message="For external authors and AI tools"
                description={
                  <Space direction="vertical" size={4}>
                    <Text>
                      Hand these files to anyone who needs to produce a{' '}
                      <Text code>.pascenario.json</Text> that this install can
                      import — including offline / airgapped authors. The JSON
                      Schema is the contract; the spec doc explains the three
                      authoring modes; the registry snapshot is optional (only
                      needed to pin specific device models).
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      Import endpoint: POST /api/v1/scenarios/import/portable
                      &nbsp;·&nbsp;
                      Live validation: POST /api/v1/scenarios/validate/portable
                    </Text>
                  </Space>
                }
              />
              <Table
                columns={columns}
                dataSource={authoringFiles}
                rowKey="filename"
                pagination={false}
                size="middle"
              />
            </Card>
          )}

          {otherFiles.length > 0 && (
            <Card
              title={
                <Space>
                  <FolderOpenOutlined />
                  <span>Documentation & Resources</span>
                </Space>
              }
              size="small"
              extra={
                presentationFiles.length === 0 && authoringFiles.length === 0 ? (
                  <Button onClick={fetchFiles} loading={isLoading} size="small">
                    Refresh
                  </Button>
                ) : undefined
              }
            >
              <Table
                columns={columns}
                dataSource={otherFiles}
                rowKey="filename"
                pagination={false}
                size="middle"
              />
            </Card>
          )}
        </>
      )}
    </Space>
  );
};

export default DownloadsTab;
