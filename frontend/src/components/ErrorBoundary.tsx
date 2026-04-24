/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Error boundary component to catch React errors
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Button, Result } from 'antd';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  private handleReset = () => {
    // Clear all localStorage and reload
    localStorage.clear();
    window.location.href = '/login';
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#1a1a2e',
            padding: 24,
          }}
        >
          <Result
            status="error"
            title="Something went wrong"
            subTitle={this.state.error?.message || 'An unexpected error occurred'}
            extra={[
              <Button type="primary" key="reset" onClick={this.handleReset}>
                Reset & Login Again
              </Button>,
              <Button key="reload" onClick={() => window.location.reload()}>
                Try Reload
              </Button>,
            ]}
            style={{
              background: '#232342',
              borderRadius: 12,
              padding: 40,
              border: '1px solid #2d2d52',
            }}
          />
          {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
            <pre
              style={{
                position: 'fixed',
                bottom: 0,
                left: 0,
                right: 0,
                background: '#0d0d1a',
                color: '#ff6b6b',
                padding: 16,
                fontSize: 12,
                maxHeight: 200,
                overflow: 'auto',
                borderTop: '1px solid #2d2d52',
              }}
            >
              {this.state.error?.stack}
              {'\n\n'}
              {this.state.errorInfo.componentStack}
            </pre>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
