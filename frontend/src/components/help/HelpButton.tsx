/**
 * HelpButton - Header button that opens the help drawer
 */

import React, { useState } from 'react';
import { Button, Tooltip } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import HelpDrawer from './HelpDrawer';

interface HelpButtonProps {
  style?: React.CSSProperties;
}

const HelpButton: React.FC<HelpButtonProps> = ({ style }) => {
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleClick = (e: React.MouseEvent) => {
    // Shift+click goes directly to help page
    if (e.shiftKey) {
      navigate('/help');
    } else {
      setDrawerOpen(true);
    }
  };

  return (
    <>
      <Tooltip title="Help (Shift+click for full page)">
        <Button
          type="text"
          icon={<QuestionCircleOutlined style={{ fontSize: 18 }} />}
          onClick={handleClick}
          style={{ color: '#a8a8c0', ...style }}
        />
      </Tooltip>

      <HelpDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </>
  );
};

export default HelpButton;
