/**
 * HelpSearch - Search component for help content
 */

import React, { useState, useMemo } from 'react';
import { Input, List, Typography, Space, Tag, Empty } from 'antd';
import { SearchOutlined, FileTextOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { searchArticles, categoryInfo, type HelpSearchResult } from '../../content/help';

const { Text, Paragraph } = Typography;

interface HelpSearchProps {
  onSelectArticle?: (articleId: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  style?: React.CSSProperties;
}

const HelpSearch: React.FC<HelpSearchProps> = ({
  onSelectArticle,
  placeholder = 'Search help articles...',
  autoFocus = false,
  style,
}) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState(false);

  const results = useMemo(() => {
    if (!query.trim()) return [];
    return searchArticles(query).slice(0, 8);
  }, [query]);

  const handleSelect = (articleId: string) => {
    setQuery('');
    if (onSelectArticle) {
      onSelectArticle(articleId);
    } else {
      navigate(`/help/${articleId}`);
    }
  };

  const showResults = focused && query.trim().length > 0;

  return (
    <div style={{ position: 'relative', ...style }}>
      <Input
        prefix={<SearchOutlined style={{ color: '#6b6b8a' }} />}
        placeholder={placeholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setTimeout(() => setFocused(false), 200)}
        autoFocus={autoFocus}
        style={{
          background: '#1e2d3d',
          border: '1px solid #2a3f54',
          color: '#fff',
        }}
        allowClear
      />

      {showResults && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            marginTop: 4,
            background: '#1a2734',
            border: '1px solid #2a3f54',
            borderRadius: 6,
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
            zIndex: 1000,
            maxHeight: 400,
            overflow: 'auto',
          }}
        >
          {results.length > 0 ? (
            <List
              size="small"
              dataSource={results}
              renderItem={(result: HelpSearchResult) => (
                <List.Item
                  onClick={() => handleSelect(result.article.id)}
                  style={{
                    cursor: 'pointer',
                    padding: '12px 16px',
                    borderBottom: '1px solid #2a3f54',
                  }}
                  className="help-search-result"
                >
                  <Space direction="vertical" size={4} style={{ width: '100%' }}>
                    <Space>
                      <FileTextOutlined style={{ color: '#049FD9' }} />
                      <Text strong style={{ color: '#fff' }}>
                        {result.article.title}
                      </Text>
                      <Tag
                        style={{
                          background: '#2a3f54',
                          border: 'none',
                          color: '#8aa4bc',
                          fontSize: 10,
                        }}
                      >
                        {categoryInfo[result.article.category].label}
                      </Tag>
                    </Space>
                    <Paragraph
                      style={{
                        color: '#6b6b8a',
                        marginBottom: 0,
                        fontSize: 12,
                      }}
                      ellipsis={{ rows: 1 }}
                    >
                      {result.article.summary}
                    </Paragraph>
                  </Space>
                </List.Item>
              )}
            />
          ) : (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={
                <Text style={{ color: '#6b6b8a' }}>
                  No results for "{query}"
                </Text>
              }
              style={{ padding: 24 }}
            />
          )}
        </div>
      )}

      <style>{`
        .help-search-result:hover {
          background: #1e2d3d !important;
        }
      `}</style>
    </div>
  );
};

export default HelpSearch;
