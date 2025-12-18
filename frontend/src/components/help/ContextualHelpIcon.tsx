/**
 * ContextualHelpIcon - Small help icon that links to a specific help article
 *
 * Use next to section headers or complex UI elements to provide
 * quick access to relevant documentation.
 */

import React from 'react';
import { Tooltip, Button } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { getArticle } from '../../content/help';

interface ContextualHelpIconProps {
  articleId: string;
  tooltip?: string;
  size?: 'small' | 'default';
  style?: React.CSSProperties;
}

const ContextualHelpIcon: React.FC<ContextualHelpIconProps> = ({
  articleId,
  tooltip,
  size = 'small',
  style,
}) => {
  const navigate = useNavigate();
  const article = getArticle(articleId);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/help/${articleId}`);
  };

  const tooltipText = tooltip || (article ? `Learn more: ${article.title}` : 'View help');

  return (
    <Tooltip title={tooltipText}>
      <Button
        type="text"
        size={size}
        icon={
          <QuestionCircleOutlined
            style={{
              fontSize: size === 'small' ? 14 : 16,
              color: '#5a9fd4',
            }}
          />
        }
        onClick={handleClick}
        style={{
          padding: size === 'small' ? '0 4px' : '0 8px',
          height: 'auto',
          minWidth: 'auto',
          ...style,
        }}
      />
    </Tooltip>
  );
};

export default ContextualHelpIcon;
