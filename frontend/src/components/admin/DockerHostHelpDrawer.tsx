/**
 * Docker Host Help Drawer
 * Provides in-context help for Docker host setup with AI-powered assistance
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  Drawer,
  Typography,
  Space,
  Button,
  Input,
  Divider,
  Tabs,
  Spin,
  Alert,
  message,
} from 'antd';
import {
  QuestionCircleOutlined,
  RobotOutlined,
  BookOutlined,
  SendOutlined,
  DeleteOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { dockerHostSetupArticle } from '../../content/help/docker-host-setup';
import apiClient from '../../api/client';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface HelpMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface DockerHostHelpDrawerProps {
  open: boolean;
  onClose: () => void;
}

const DockerHostHelpDrawer: React.FC<DockerHostHelpDrawerProps> = ({
  open,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<string>('guide');
  const [messages, setMessages] = useState<HelpMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Reset state when drawer closes
  useEffect(() => {
    if (!open) {
      setActiveTab('guide');
      setError(null);
    }
  }, [open]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: HelpMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.post<{ response: string }>(
        '/api/v1/ai/help',
        {
          question: userMessage.content,
          context: 'docker_host_setup',
        }
      );

      const assistantMessage: HelpMessage = {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Failed to get AI response:', err);
      setError('Failed to get a response. Please check your AI provider settings.');

      // Add error message to chat
      const errorMessage: HelpMessage = {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: 'I apologize, but I encountered an error processing your question. Please ensure the AI provider is configured in Settings > AI Provider, or try again later.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setError(null);
    message.success('Chat cleared');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const ContentComponent = dockerHostSetupArticle.content;

  const suggestedQuestions = [
    'How do I generate TLS certificates?',
    'What firewall ports need to be open?',
    'How do I test the Docker connection?',
    'What if Docker won\'t start after configuration?',
    'How do I find my network interfaces?',
  ];

  return (
    <Drawer
      title={
        <Space>
          <QuestionCircleOutlined style={{ color: '#049FD9' }} />
          <span style={{ color: '#fff' }}>Docker Host Setup Help</span>
        </Space>
      }
      placement="right"
      width={640}
      open={open}
      onClose={onClose}
      styles={{
        header: {
          background: '#0d0d1a',
          borderBottom: '1px solid #2d2d52',
        },
        body: {
          background: '#1a1a2e',
          padding: 0,
        },
      }}
    >
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        style={{ height: '100%' }}
        tabBarStyle={{
          background: '#1a1a2e',
          margin: 0,
          padding: '0 16px',
          borderBottom: '1px solid #2d2d52',
        }}
        items={[
          {
            key: 'guide',
            label: (
              <Space>
                <BookOutlined />
                Setup Guide
              </Space>
            ),
            children: (
              <div
                style={{
                  padding: 16,
                  height: 'calc(100vh - 140px)',
                  overflowY: 'auto',
                }}
                className="help-article-content"
              >
                <ContentComponent />
              </div>
            ),
          },
          {
            key: 'ai',
            label: (
              <Space>
                <RobotOutlined />
                Ask AI
              </Space>
            ),
            children: (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  height: 'calc(100vh - 140px)',
                }}
              >
                {/* Messages Area */}
                <div
                  style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: 16,
                  }}
                >
                  {messages.length === 0 ? (
                    <Space direction="vertical" size="large" style={{ width: '100%' }}>
                      <div style={{ textAlign: 'center', padding: '24px 0' }}>
                        <RobotOutlined
                          style={{
                            fontSize: 48,
                            color: '#049FD9',
                            marginBottom: 16,
                          }}
                        />
                        <Title level={5} style={{ color: '#fff', marginBottom: 8 }}>
                          Ask AI for Help
                        </Title>
                        <Paragraph style={{ color: '#8aa4bc' }}>
                          Have questions about setting up a Docker host? Ask me anything
                          about TLS certificates, firewall configuration, troubleshooting,
                          or any other Docker-related topics.
                        </Paragraph>
                      </div>

                      <Divider style={{ borderColor: '#2d2d52', margin: '12px 0' }}>
                        <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                          SUGGESTED QUESTIONS
                        </Text>
                      </Divider>

                      <Space direction="vertical" size="small" style={{ width: '100%' }}>
                        {suggestedQuestions.map((question, idx) => (
                          <Button
                            key={idx}
                            type="text"
                            block
                            onClick={() => {
                              setInputValue(question);
                            }}
                            style={{
                              textAlign: 'left',
                              color: '#5a9fd4',
                              background: '#1e2d3d',
                              border: '1px solid #2a3f54',
                              height: 'auto',
                              padding: '8px 12px',
                              whiteSpace: 'normal',
                            }}
                          >
                            {question}
                          </Button>
                        ))}
                      </Space>
                    </Space>
                  ) : (
                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                      {messages.map((msg) => (
                        <div
                          key={msg.id}
                          style={{
                            display: 'flex',
                            justifyContent:
                              msg.role === 'user' ? 'flex-end' : 'flex-start',
                          }}
                        >
                          <div
                            style={{
                              maxWidth: '85%',
                              padding: '10px 14px',
                              borderRadius: 8,
                              background:
                                msg.role === 'user' ? '#049FD9' : '#1e2d3d',
                              border:
                                msg.role === 'assistant'
                                  ? '1px solid #2a3f54'
                                  : 'none',
                            }}
                          >
                            <Text
                              style={{
                                color: '#fff',
                                whiteSpace: 'pre-wrap',
                                wordBreak: 'break-word',
                              }}
                            >
                              {msg.content}
                            </Text>
                          </div>
                        </div>
                      ))}
                      {isLoading && (
                        <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                          <div
                            style={{
                              padding: '10px 14px',
                              borderRadius: 8,
                              background: '#1e2d3d',
                              border: '1px solid #2a3f54',
                            }}
                          >
                            <Space>
                              <LoadingOutlined spin />
                              <Text style={{ color: '#8aa4bc' }}>Thinking...</Text>
                            </Space>
                          </div>
                        </div>
                      )}
                      <div ref={messagesEndRef} />
                    </Space>
                  )}
                </div>

                {/* Error Alert */}
                {error && (
                  <Alert
                    message={error}
                    type="error"
                    showIcon
                    closable
                    onClose={() => setError(null)}
                    style={{
                      margin: '0 16px',
                      background: '#1e2d3d',
                      border: '1px solid #ff4d4f',
                    }}
                  />
                )}

                {/* Input Area */}
                <div
                  style={{
                    padding: 16,
                    borderTop: '1px solid #2d2d52',
                    background: '#0d0d1a',
                  }}
                >
                  <Space.Compact style={{ width: '100%' }}>
                    <TextArea
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Ask a question about Docker host setup..."
                      autoSize={{ minRows: 1, maxRows: 4 }}
                      style={{
                        background: '#1a1a2e',
                        border: '1px solid #2d2d52',
                        color: '#fff',
                      }}
                      disabled={isLoading}
                    />
                    <Button
                      type="primary"
                      icon={isLoading ? <LoadingOutlined spin /> : <SendOutlined />}
                      onClick={handleSendMessage}
                      disabled={!inputValue.trim() || isLoading}
                      style={{ height: 'auto' }}
                    >
                      Send
                    </Button>
                  </Space.Compact>
                  {messages.length > 0 && (
                    <div style={{ marginTop: 8, textAlign: 'right' }}>
                      <Button
                        type="text"
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={handleClearChat}
                        style={{ color: '#6b6b8a' }}
                      >
                        Clear chat
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            ),
          },
        ]}
      />
    </Drawer>
  );
};

export default DockerHostHelpDrawer;
