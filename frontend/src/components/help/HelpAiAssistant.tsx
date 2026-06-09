/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * HelpAiAssistant - Ask-AI box for the help system.
 *
 * Sends questions to the backend AI help endpoint (/api/v1/ai/help), passing a
 * context derived from the route the user opened help from, so answers use the
 * matching domain prompt + skills (scenario_studio, attack_config, ...).
 */

import React, { useState } from 'react';
import { Typography, Space, Input, Button, Alert, Spin } from 'antd';
import { RobotOutlined, SendOutlined } from '@ant-design/icons';
import { aiApi } from '../../api/ai';
import { useFeatures } from '../../hooks/useFeatures';
import { extractErrorMessage } from '../../utils/errorUtils';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, BG_INSET, CARD_STYLE } from '../../constants/theme';

const { Text, Paragraph } = Typography;

/** Map the route help was opened from to a backend AI help context. */
export function helpContextForRoute(pathname: string): string {
  if (pathname.startsWith('/studio')) return 'scenario_studio';
  if (pathname.startsWith('/cyber-vision')) return 'cyber_vision';
  if (pathname.startsWith('/libraries/attacks')) return 'attack_config';
  if (pathname.startsWith('/libraries')) return 'device_config';
  if (pathname.startsWith('/live-traffic') || pathname.startsWith('/agents')) return 'deployment';
  return 'general';
}

interface Turn {
  question: string;
  answer: string;
}

interface HelpAiAssistantProps {
  /** Route the user opened help from; drives the backend context. */
  routePath: string;
}

const HelpAiAssistant: React.FC<HelpAiAssistantProps> = ({ routePath }) => {
  const { aiEnabled } = useFeatures();
  const [question, setQuestion] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!aiEnabled) return null;

  const handleAsk = async () => {
    const q = question.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    try {
      const answer = await aiApi.helpChat(q, helpContextForRoute(routePath));
      setTurns((prev) => [...prev, { question: q, answer }]);
      setQuestion('');
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ ...CARD_STYLE, padding: 12, borderRadius: 8 }}>
      <Space style={{ marginBottom: 8 }}>
        <RobotOutlined style={{ color: ACCENT_BLUE }} />
        <Text strong style={{ color: '#fff' }}>Ask AI</Text>
        <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
          answers use your configured AI provider
        </Text>
      </Space>

      {turns.length > 0 && (
        <div style={{ maxHeight: 280, overflowY: 'auto', marginBottom: 8 }}>
          {turns.map((turn, i) => (
            <div key={i} style={{ marginBottom: 12 }}>
              <Paragraph style={{ color: '#fff', marginBottom: 4 }}>
                <Text strong style={{ color: ACCENT_BLUE }}>You: </Text>
                {turn.question}
              </Paragraph>
              <Paragraph
                style={{
                  color: TEXT_PARAGRAPH,
                  background: BG_INSET,
                  border: `1px solid ${BORDER_DEFAULT}`,
                  borderRadius: 6,
                  padding: 8,
                  marginBottom: 0,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {turn.answer}
              </Paragraph>
            </div>
          ))}
        </div>
      )}

      {error && (
        <Alert
          type="error"
          showIcon
          message={error}
          style={{ marginBottom: 8 }}
          closable
          onClose={() => setError(null)}
        />
      )}

      <Space.Compact style={{ width: '100%' }}>
        <Input
          placeholder="Ask a question about PacketArch…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onPressEnter={handleAsk}
          disabled={loading}
        />
        <Button
          type="primary"
          icon={loading ? <Spin size="small" /> : <SendOutlined />}
          onClick={handleAsk}
          disabled={loading || !question.trim()}
        />
      </Space.Compact>
    </div>
  );
};

export default HelpAiAssistant;
