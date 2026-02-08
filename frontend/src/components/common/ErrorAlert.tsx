import React from 'react';
import { Alert } from 'antd';

export interface ErrorAlertProps {
  /** Error message string, or null/undefined to hide */
  error: string | null | undefined;
  /** Callback to clear the error */
  onClose: () => void;
  /** If true, show error as the message directly (no title/description split). Default: false */
  compact?: boolean;
  /** Override the title. Default: "Error" */
  title?: string;
  /** Additional style */
  style?: React.CSSProperties;
}

const ErrorAlert: React.FC<ErrorAlertProps> = ({
  error,
  onClose,
  compact = false,
  title = 'Error',
  style,
}) => {
  if (!error) return null;

  if (compact) {
    return (
      <Alert
        message={error}
        type="error"
        showIcon
        closable
        onClose={onClose}
        style={style}
      />
    );
  }

  return (
    <Alert
      message={title}
      description={error}
      type="error"
      showIcon
      closable
      onClose={onClose}
      style={style}
    />
  );
};

export default ErrorAlert;
