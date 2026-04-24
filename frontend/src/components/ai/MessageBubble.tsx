/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Message Bubble - Display individual messages with markdown rendering
 */

import React, { useState } from 'react';
import { Card, Typography, Space, Collapse, Button, Tooltip } from 'antd';
import {
  UserOutlined,
  RobotOutlined,
  ToolOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CopyOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message, ToolCall } from '../../stores/aiAssistantStore';

const { Text } = Typography;

// Code block component with copy button
interface CodeBlockProps {
  language?: string;
  children: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ language, children }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ position: 'relative', marginTop: 8, marginBottom: 8 }}>
      <Tooltip title={copied ? 'Copied!' : 'Copy code'}>
        <Button
          icon={copied ? <CheckOutlined /> : <CopyOutlined />}
          size="small"
          type="text"
          onClick={handleCopy}
          style={{
            position: 'absolute',
            top: 4,
            right: 4,
            zIndex: 1,
            color: copied ? '#52c41a' : '#8aa4bc',
            background: 'rgba(26, 39, 52, 0.8)',
          }}
        />
      </Tooltip>
      <SyntaxHighlighter
        style={oneDark}
        language={language || 'text'}
        PreTag="div"
        customStyle={{
          margin: 0,
          borderRadius: 6,
          fontSize: 12,
        }}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  );
};

// Tool call badge component
interface ToolBadgeProps {
  tool: ToolCall;
}

const ToolBadge: React.FC<ToolBadgeProps> = ({ tool }) => {
  return (
    <Space size={4}>
      {tool.success === undefined ? (
        <ToolOutlined style={{ fontSize: 12, color: '#8aa4bc' }} />
      ) : tool.success ? (
        <CheckCircleOutlined style={{ fontSize: 12, color: '#52c41a' }} />
      ) : (
        <CloseCircleOutlined style={{ fontSize: 12, color: '#ff4d4f' }} />
      )}
      <Text style={{ fontSize: 12, color: '#8aa4bc' }}>
        {tool.name}
      </Text>
      {tool.executionTime && (
        <Text style={{ fontSize: 10, color: '#6a8caf' }}>
          {tool.executionTime}ms
        </Text>
      )}
    </Space>
  );
};

interface MessageBubbleProps {
  message: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        width: '100%',
      }}
    >
      <Card
        size="small"
        style={{
          maxWidth: '85%',
          backgroundColor: isUser ? '#1a3a5c' : '#253545',
          borderColor: isUser ? '#2a5a8c' : '#3a5068',
        }}
        styles={{
          body: {
            padding: '12px',
          },
        }}
      >
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          {/* Header */}
          <Space size={8}>
            {isUser ? (
              <UserOutlined style={{ color: '#5a9fd4' }} />
            ) : (
              <RobotOutlined style={{ color: '#52c41a' }} />
            )}
            <Text strong style={{ fontSize: 12, color: '#e0e8f0' }}>
              {isUser ? 'You' : 'AI Assistant'}
            </Text>
            <Text style={{ fontSize: 11, color: '#6a8caf' }}>
              {new Date(message.timestamp).toLocaleTimeString()}
            </Text>
          </Space>

          {/* Message content with markdown rendering */}
          <div
            className="markdown-content"
            style={{
              color: '#c5d8ee',
              fontSize: 14,
              lineHeight: 1.6,
            }}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code: ({ className, children, ...props }) => {
                  const match = /language-(\w+)/.exec(className || '');
                  const codeString = String(children).replace(/\n$/, '');
                  // Check if it's an inline code or block
                  const isInline = !match && !codeString.includes('\n');
                  return isInline ? (
                    <code
                      style={{
                        backgroundColor: '#1a2734',
                        padding: '2px 6px',
                        borderRadius: 4,
                        fontSize: 12,
                        color: '#e0a882',
                      }}
                      {...props}
                    >
                      {children}
                    </code>
                  ) : (
                    <CodeBlock language={match?.[1]}>{codeString}</CodeBlock>
                  );
                },
                p: ({ children }) => (
                  <p style={{ margin: '8px 0' }}>{children}</p>
                ),
                ul: ({ children }) => (
                  <ul style={{ margin: '8px 0', paddingLeft: 20 }}>{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol style={{ margin: '8px 0', paddingLeft: 20 }}>{children}</ol>
                ),
                li: ({ children }) => (
                  <li style={{ margin: '4px 0' }}>{children}</li>
                ),
                h1: ({ children }) => (
                  <h1 style={{ fontSize: 20, margin: '16px 0 8px', color: '#e0e8f0' }}>{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 style={{ fontSize: 18, margin: '14px 0 6px', color: '#e0e8f0' }}>{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 style={{ fontSize: 16, margin: '12px 0 4px', color: '#e0e8f0' }}>{children}</h3>
                ),
                blockquote: ({ children }) => (
                  <blockquote
                    style={{
                      borderLeft: '3px solid #5a9fd4',
                      paddingLeft: 12,
                      margin: '8px 0',
                      color: '#a8c4e0',
                    }}
                  >
                    {children}
                  </blockquote>
                ),
                table: ({ children }) => (
                  <table
                    style={{
                      borderCollapse: 'collapse',
                      margin: '8px 0',
                      width: '100%',
                    }}
                  >
                    {children}
                  </table>
                ),
                th: ({ children }) => (
                  <th
                    style={{
                      border: '1px solid #3a5068',
                      padding: '8px',
                      backgroundColor: '#1a2734',
                      textAlign: 'left',
                    }}
                  >
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td style={{ border: '1px solid #3a5068', padding: '8px' }}>{children}</td>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#5a9fd4' }}
                  >
                    {children}
                  </a>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>

          {/* Tool calls (if any) */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <Collapse
              size="small"
              ghost
              items={message.toolCalls.map((tool, index) => ({
                key: index.toString(),
                label: <ToolBadge tool={tool} />,
                children: (
                  <div>
                    <Text style={{ fontSize: 11, color: '#6a8caf' }}>
                      Input:
                    </Text>
                    <CodeBlock language="json">
                      {JSON.stringify(tool.input, null, 2)}
                    </CodeBlock>
                    {tool.result && (
                      <>
                        <Text style={{ fontSize: 11, marginTop: 8, color: '#6a8caf' }}>
                          Result:
                        </Text>
                        <CodeBlock language="json">{tool.result}</CodeBlock>
                      </>
                    )}
                  </div>
                ),
              }))}
            />
          )}
        </Space>
      </Card>
    </div>
  );
};

export default MessageBubble;
