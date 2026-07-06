/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */

import React from 'react';
import { Button, Space, Typography, theme } from 'antd';
import { ExportOutlined, PrinterOutlined, DownloadOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const ReleaseNotesTab: React.FC = () => {
  const { token } = theme.useToken();

  const handleSaveAsPdf = () => {
    // Open in new tab so the user can Ctrl+P / Cmd+P to print
    const w = window.open('/release-notes.html', '_blank', 'noopener,noreferrer');
    w?.focus();
  };

  const handleDownloadHtml = () => {
    const a = document.createElement('a');
    a.href = '/release-notes.html';
    a.download = 'packetarch-release-notes.html';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <Space direction="vertical" size={20} style={{ width: '100%' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div>
          <Title level={4} style={{ margin: 0, marginBottom: 4 }}>
            Release Notes
          </Title>
          <Text type="secondary">
            v1.10.0 &rarr; v1.13.0 &nbsp;&middot;&nbsp; June 17 &ndash; July 2, 2026
          </Text>
        </div>
        <Space wrap>
          <Button icon={<PrinterOutlined />} onClick={handleSaveAsPdf}>
            Save as PDF
          </Button>
          <Button icon={<DownloadOutlined />} onClick={handleDownloadHtml}>
            Download HTML
          </Button>
          <Button
            icon={<ExportOutlined />}
            onClick={() => window.open('/release-notes.html', '_blank', 'noopener,noreferrer')}
          >
            Open in new tab
          </Button>
        </Space>
      </div>

      <div
        style={{
          border: `1px solid ${token.colorBorder}`,
          borderRadius: token.borderRadius,
          overflow: 'hidden',
        }}
      >
        <iframe
          src="/release-notes.html"
          title="PacketArch Release Notes"
          style={{
            display: 'block',
            width: '100%',
            height: 'calc(100vh - 320px)',
            minHeight: 500,
            border: 'none',
          }}
        />
      </div>
    </Space>
  );
};

export default ReleaseNotesTab;
