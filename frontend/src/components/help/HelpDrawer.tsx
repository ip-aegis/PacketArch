/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * HelpDrawer - Slide-out drawer for quick help access
 */

import React, { useState } from 'react';
import { Drawer, Typography, Button, Space, Divider } from 'antd';
import { ExpandOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import HelpSearch from './HelpSearch';
import HelpTOC from './HelpTOC';
import HelpArticle from './HelpArticle';
import { getArticleForRoute } from '../../content/help';

const { Title, Paragraph } = Typography;

interface HelpDrawerProps {
  open: boolean;
  onClose: () => void;
}

const HelpDrawer: React.FC<HelpDrawerProps> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [selectedArticle, setSelectedArticle] = useState<string | null>(null);

  const handleSelectArticle = (articleId: string) => {
    setSelectedArticle(articleId);
  };

  const handleOpenFullHelp = () => {
    onClose();
    if (selectedArticle) {
      navigate(`/help/${selectedArticle}`);
    } else {
      navigate('/help');
    }
  };

  const handleBack = () => {
    setSelectedArticle(null);
  };

  // When the drawer opens, jump straight to the article matching the current
  // route if one exists. When it closes, reset so the next open re-evaluates.
  React.useEffect(() => {
    if (open) {
      const match = getArticleForRoute(location.pathname);
      setSelectedArticle(match ? match.id : null);
    } else {
      setSelectedArticle(null);
    }
  }, [open, location.pathname]);

  return (
    <Drawer
      title={
        <Space>
          <QuestionCircleOutlined style={{ color: '#049FD9' }} />
          <span style={{ color: '#fff' }}>Help</span>
        </Space>
      }
      placement="right"
      width={480}
      open={open}
      onClose={onClose}
      styles={{
        header: {
          background: '#0d0d1a',
          borderBottom: '1px solid #2d2d52',
        },
        body: {
          background: '#1a1a2e',
          padding: 16,
        },
      }}
      extra={
        <Button
          type="text"
          icon={<ExpandOutlined />}
          onClick={handleOpenFullHelp}
          style={{ color: '#5a9fd4' }}
        >
          Open Full Help
        </Button>
      }
    >
      {selectedArticle ? (
        // Article View
        <div>
          <Button
            type="text"
            onClick={handleBack}
            style={{ color: '#5a9fd4', marginBottom: 12, padding: 0 }}
          >
            &larr; Back to topics
          </Button>
          <HelpArticle
            articleId={selectedArticle}
            showBackButton={false}
            showRelated={false}
            onNavigate={handleSelectArticle}
          />
        </div>
      ) : (
        // Browse View
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Title level={5} style={{ color: '#fff', marginBottom: 8 }}>
              What do you need help with?
            </Title>
            <HelpSearch onSelectArticle={handleSelectArticle} autoFocus />
          </div>

          <Divider style={{ borderColor: '#2d2d52', margin: '12px 0' }} />

          <div>
            <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
              Browse Topics
            </Title>
            <HelpTOC
              onSelectArticle={handleSelectArticle}
              collapsed
            />
          </div>

          <Divider style={{ borderColor: '#2d2d52', margin: '12px 0' }} />

          <div style={{ textAlign: 'center', padding: '8px 0' }}>
            <Paragraph style={{ color: '#6b6b8a', marginBottom: 8 }}>
              Need more detailed documentation?
            </Paragraph>
            <Button type="primary" onClick={handleOpenFullHelp}>
              Open Full Help Page
            </Button>
          </div>
        </Space>
      )}
    </Drawer>
  );
};

export default HelpDrawer;
