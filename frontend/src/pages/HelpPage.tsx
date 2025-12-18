/**
 * HelpPage - Main help documentation page
 */

import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Typography, Row, Col, Card, Space, Grid } from 'antd';
import {
  QuestionCircleOutlined,
  RocketOutlined,
  FolderOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  SafetyOutlined,
  SettingOutlined,
  BookOutlined,
} from '@ant-design/icons';
import HelpSearch from '../components/help/HelpSearch';
import HelpTOC from '../components/help/HelpTOC';
import HelpArticle from '../components/help/HelpArticle';
import {
  getAllArticles,
  categoryInfo,
  type HelpCategory,
} from '../content/help';

const { Title, Paragraph, Text } = Typography;
const { useBreakpoint } = Grid;

const categoryIcons: Record<HelpCategory, React.ReactNode> = {
  'getting-started': <RocketOutlined style={{ fontSize: 24 }} />,
  'scenarios': <FolderOutlined style={{ fontSize: 24 }} />,
  'traffic-generation': <CloudServerOutlined style={{ fontSize: 24 }} />,
  'device-management': <DatabaseOutlined style={{ fontSize: 24 }} />,
  'security-testing': <SafetyOutlined style={{ fontSize: 24 }} />,
  'administration': <SettingOutlined style={{ fontSize: 24 }} />,
  'reference': <BookOutlined style={{ fontSize: 24 }} />,
};

const HelpPage: React.FC = () => {
  const { articleId } = useParams<{ articleId?: string }>();
  const navigate = useNavigate();
  const screens = useBreakpoint();

  const handleSelectArticle = (id: string) => {
    if (id) {
      navigate(`/help/${id}`);
    } else {
      navigate('/help');
    }
  };

  // Get unique categories with their first article for quick access cards
  const categories = Object.entries(categoryInfo)
    .sort(([, a], [, b]) => a.order - b.order)
    .map(([category, info]) => {
      const articles = getAllArticles().filter((a) => a.category === category);
      return {
        category: category as HelpCategory,
        ...info,
        articleCount: articles.length,
        firstArticle: articles[0],
      };
    });

  // Responsive layout
  const showSidebar = screens.lg;

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ color: '#fff', marginBottom: 8 }}>
          <QuestionCircleOutlined style={{ marginRight: 12, color: '#049FD9' }} />
          Help & Documentation
        </Title>
        <Paragraph style={{ color: '#8aa4bc', fontSize: 15 }}>
          Learn how to use PacketArch to create realistic OT traffic scenarios for security testing and validation.
        </Paragraph>
      </div>

      {/* Search */}
      <Card
        style={{
          background: '#1a2734',
          border: '1px solid #2a3f54',
          marginBottom: 24,
        }}
      >
        <HelpSearch
          onSelectArticle={handleSelectArticle}
          placeholder="Search for topics, features, or keywords..."
          autoFocus={!articleId}
        />
      </Card>

      {articleId ? (
        // Article View
        <Row gutter={24}>
          {showSidebar && (
            <Col span={6}>
              <div style={{ position: 'sticky', top: 24 }}>
                <HelpTOC
                  selectedArticleId={articleId}
                  onSelectArticle={handleSelectArticle}
                />
              </div>
            </Col>
          )}
          <Col span={showSidebar ? 18 : 24}>
            <HelpArticle
              articleId={articleId}
              showBackButton={!showSidebar}
              onNavigate={handleSelectArticle}
            />
          </Col>
        </Row>
      ) : (
        // Home View - Category Cards
        <>
          {/* Quick Start */}
          <Card
            style={{
              background: 'linear-gradient(135deg, #1a2734 0%, #152330 100%)',
              border: '1px solid #2a3f54',
              marginBottom: 24,
            }}
          >
            <Row align="middle" gutter={24}>
              <Col flex="auto">
                <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
                  <RocketOutlined style={{ marginRight: 8, color: '#049FD9' }} />
                  New to PacketArch?
                </Title>
                <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
                  Start with our Getting Started guide to learn the basics of creating OT traffic scenarios.
                </Paragraph>
              </Col>
              <Col>
                <Card
                  hoverable
                  onClick={() => handleSelectArticle('getting-started')}
                  style={{
                    background: '#049FD9',
                    border: 'none',
                    cursor: 'pointer',
                  }}
                  bodyStyle={{ padding: '12px 24px' }}
                >
                  <Text strong style={{ color: '#fff' }}>
                    Get Started
                  </Text>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* Category Grid */}
          <Row gutter={[16, 16]}>
            {categories.map(({ category, label, articleCount, firstArticle }) => (
              <Col xs={24} sm={12} lg={8} key={category}>
                <Card
                  hoverable
                  onClick={() => firstArticle && handleSelectArticle(firstArticle.id)}
                  style={{
                    background: '#1a2734',
                    border: '1px solid #2a3f54',
                    height: '100%',
                    cursor: 'pointer',
                  }}
                  bodyStyle={{ height: '100%' }}
                >
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <div
                      style={{
                        width: 48,
                        height: 48,
                        borderRadius: 8,
                        background: '#1e2d3d',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#049FD9',
                        marginBottom: 8,
                      }}
                    >
                      {categoryIcons[category]}
                    </div>
                    <Title level={5} style={{ color: '#fff', marginBottom: 4 }}>
                      {label}
                    </Title>
                    <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                      {articleCount} article{articleCount !== 1 ? 's' : ''}
                    </Text>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>

          {/* All Articles */}
          <Card
            style={{
              background: '#1a2734',
              border: '1px solid #2a3f54',
              marginTop: 24,
            }}
          >
            <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
              All Articles
            </Title>
            <HelpTOC onSelectArticle={handleSelectArticle} />
          </Card>
        </>
      )}
    </div>
  );
};

export default HelpPage;
