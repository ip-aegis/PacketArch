/**
 * HelpTOC - Table of Contents component for help navigation
 */

import React from 'react';
import { Menu, Typography } from 'antd';
import type { MenuProps } from 'antd';
import {
  RocketOutlined,
  FolderOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  SafetyOutlined,
  SettingOutlined,
  BookOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  getArticlesByCategory,
  categoryInfo,
  type HelpCategory,
} from '../../content/help';

const { Text } = Typography;

interface HelpTOCProps {
  selectedArticleId?: string;
  onSelectArticle?: (articleId: string) => void;
  collapsed?: boolean;
  style?: React.CSSProperties;
}

const categoryIcons: Record<HelpCategory, React.ReactNode> = {
  'getting-started': <RocketOutlined />,
  'scenarios': <FolderOutlined />,
  'traffic-generation': <CloudServerOutlined />,
  'device-management': <DatabaseOutlined />,
  'security-testing': <SafetyOutlined />,
  'administration': <SettingOutlined />,
  'reference': <BookOutlined />,
};

const HelpTOC: React.FC<HelpTOCProps> = ({
  selectedArticleId,
  onSelectArticle,
  collapsed = false,
  style,
}) => {
  const navigate = useNavigate();
  const articlesByCategory = getArticlesByCategory();

  const handleClick: MenuProps['onClick'] = (info) => {
    const articleId = info.key;
    if (onSelectArticle) {
      onSelectArticle(articleId);
    } else {
      navigate(`/help/${articleId}`);
    }
  };

  // Build menu items from categories and articles
  const menuItems: MenuProps['items'] = Array.from(articlesByCategory.entries())
    .sort(([catA], [catB]) => {
      return categoryInfo[catA].order - categoryInfo[catB].order;
    })
    .map(([category, articles]) => ({
      key: category,
      icon: categoryIcons[category],
      label: (
        <Text style={{ color: '#a8a8c0' }}>
          {categoryInfo[category].label}
        </Text>
      ),
      children: articles.map((article) => ({
        key: article.id,
        label: (
          <Text
            style={{
              color: selectedArticleId === article.id ? '#049FD9' : '#8aa4bc',
            }}
          >
            {article.title}
          </Text>
        ),
      })),
    }));

  // Determine which categories should be open
  const defaultOpenKeys = Array.from(articlesByCategory.keys());

  return (
    <div
      style={{
        background: '#1a2734',
        border: '1px solid #2a3f54',
        borderRadius: 6,
        overflow: 'hidden',
        ...style,
      }}
    >
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #2a3f54',
          background: '#152330',
        }}
      >
        <Text strong style={{ color: '#fff' }}>
          Contents
        </Text>
      </div>
      <Menu
        mode="inline"
        selectedKeys={selectedArticleId ? [selectedArticleId] : []}
        defaultOpenKeys={collapsed ? [] : defaultOpenKeys}
        onClick={handleClick}
        style={{
          background: 'transparent',
          border: 'none',
        }}
        items={menuItems}
      />
    </div>
  );
};

export default HelpTOC;
