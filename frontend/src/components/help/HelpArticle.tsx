/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * HelpArticle - Renders a single help article with related articles
 */

import React from 'react';
import { Card, Typography, Space, Tag, Divider, Button, Empty } from 'antd';
import { ArrowLeftOutlined, LinkOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  getArticle,
  getRelatedArticles,
  categoryInfo,
} from '../../content/help';

const { Title, Text, Paragraph } = Typography;

interface HelpArticleProps {
  articleId: string;
  showBackButton?: boolean;
  showRelated?: boolean;
  onNavigate?: (articleId: string) => void;
  style?: React.CSSProperties;
}

const HelpArticleComponent: React.FC<HelpArticleProps> = ({
  articleId,
  showBackButton = false,
  showRelated = true,
  onNavigate,
  style,
}) => {
  const navigate = useNavigate();
  const article = getArticle(articleId);
  const relatedArticles = showRelated ? getRelatedArticles(articleId) : [];

  const handleNavigate = (id: string) => {
    if (onNavigate) {
      onNavigate(id);
    } else {
      navigate(`/help/${id}`);
    }
  };

  const handleBack = () => {
    if (onNavigate) {
      onNavigate('');
    } else {
      navigate('/help');
    }
  };

  if (!article) {
    return (
      <Card style={{ background: '#1a2734', border: '1px solid #2a3f54', ...style }}>
        <Empty
          description={
            <Text style={{ color: '#6b6b8a' }}>
              Article not found: {articleId}
            </Text>
          }
        />
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Button type="primary" onClick={handleBack}>
            Back to Help
          </Button>
        </div>
      </Card>
    );
  }

  const ContentComponent = article.content;

  return (
    <div style={style}>
      <Card
        style={{
          background: '#1a2734',
          border: '1px solid #2a3f54',
        }}
      >
        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          {showBackButton && (
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={handleBack}
              style={{ color: '#5a9fd4', marginBottom: 12, padding: 0 }}
            >
              Back to Help
            </Button>
          )}

          <Space style={{ marginBottom: 8 }}>
            <Tag
              style={{
                background: '#2a3f54',
                border: 'none',
                color: '#8aa4bc',
              }}
            >
              {categoryInfo[article.category].label}
            </Tag>
          </Space>

          <Title level={3} style={{ color: '#fff', marginBottom: 8 }}>
            {article.title}
          </Title>

          <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
            {article.summary}
          </Paragraph>
        </div>

        <Divider style={{ borderColor: '#2a3f54', margin: '16px 0' }} />

        {/* Content */}
        <div className="help-article-content">
          <ContentComponent />
        </div>
      </Card>

      {/* Related Articles */}
      {showRelated && relatedArticles.length > 0 && (
        <Card
          style={{
            background: '#1a2734',
            border: '1px solid #2a3f54',
            marginTop: 16,
          }}
        >
          <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
            <LinkOutlined style={{ marginRight: 8 }} />
            Related Articles
          </Title>
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            {relatedArticles.map((related) => (
              <div
                key={related.id}
                onClick={() => handleNavigate(related.id)}
                style={{
                  padding: '8px 12px',
                  background: '#1e2d3d',
                  borderRadius: 4,
                  cursor: 'pointer',
                  border: '1px solid transparent',
                  transition: 'border-color 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#2a3f54';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'transparent';
                }}
              >
                <Text strong style={{ color: '#5a9fd4' }}>
                  {related.title}
                </Text>
                <Paragraph
                  style={{
                    color: '#6b6b8a',
                    marginBottom: 0,
                    fontSize: 12,
                  }}
                  ellipsis={{ rows: 1 }}
                >
                  {related.summary}
                </Paragraph>
              </div>
            ))}
          </Space>
        </Card>
      )}
    </div>
  );
};

export default HelpArticleComponent;
