import React from 'react';
import { Spin } from 'antd';

export interface LoadingSpinnerProps {
  /** Padding around the spinner in px. Default: 24 */
  padding?: number;
  /** Ant Design spin size. Default: 'default' */
  size?: 'small' | 'default' | 'large';
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  padding = 24,
  size,
}) => (
  <div style={{ textAlign: 'center', padding }}>
    <Spin size={size} />
  </div>
);

export default LoadingSpinner;
