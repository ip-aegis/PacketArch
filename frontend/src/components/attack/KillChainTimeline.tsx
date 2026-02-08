/**
 * KillChainTimeline - Live attack kill-chain progress visualization.
 * Modeled on PhaseTimeline but with red-tinted attack styling.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { Button, Space, Tag, Tooltip, Typography } from 'antd';
import {
  ForwardOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { attacksApi } from '../../api/attacks';
import type { AttackState } from '../../types/attackPlaybook';

const { Text } = Typography;

interface KillChainTimelineProps {
  scenarioId: string;
  isRunning: boolean;
  /** Pre-loaded attack state from dashboard polling (optional) */
  attackState?: AttackState | null;
  /** Pre-loaded stage info (optional — avoids extra API call) */
  stages?: { stage_id: string; name: string; color: string; duration_seconds: number }[];
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

const KillChainTimeline: React.FC<KillChainTimelineProps> = ({
  scenarioId,
  isRunning,
  attackState: externalState,
  stages,
}) => {
  const [state, setState] = useState<AttackState | null>(null);
  const [loading, setLoading] = useState(false);

  // Use external state if provided (from dashboard polling), else poll ourselves
  const currentState = externalState ?? state;

  const fetchState = useCallback(async () => {
    if (externalState !== undefined) return; // Using external state
    try {
      const s = await attacksApi.getAttackState(scenarioId);
      if (s.is_active || s.is_completed) {
        setState(s);
      } else {
        setState(null);
      }
    } catch {
      // Silently ignore
    }
  }, [scenarioId, externalState]);

  useEffect(() => {
    if (!isRunning || externalState !== undefined) {
      if (!isRunning) setState(null);
      return;
    }
    fetchState();
    const interval = setInterval(fetchState, 3000);
    return () => clearInterval(interval);
  }, [isRunning, fetchState, externalState]);

  const handleSkip = async () => {
    setLoading(true);
    try {
      await attacksApi.advanceStage(scenarioId);
      await fetchState();
    } catch (err) {
      console.error('Failed to advance stage:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePause = async () => {
    if (!currentState) return;
    setLoading(true);
    try {
      await attacksApi.pauseAttack(scenarioId, !currentState.is_paused);
      await fetchState();
    } catch (err) {
      console.error('Failed to toggle pause:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    setLoading(true);
    try {
      await attacksApi.startAttack(scenarioId, '');
      await fetchState();
    } catch (err) {
      console.error('Failed to start attack:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await attacksApi.stopAttack(scenarioId);
      await fetchState();
    } catch (err) {
      console.error('Failed to stop attack:', err);
    } finally {
      setLoading(false);
    }
  };

  if (!currentState || (!currentState.is_active && !currentState.is_completed)) {
    return null;
  }

  // Build stage list from props or infer from state
  const stageList = stages ?? Array.from({ length: currentState.total_stages }, (_, i) => ({
    stage_id: `stage_${i}`,
    name: i === currentState.current_stage_index ? currentState.current_stage_name : `Stage ${i + 1}`,
    color: i === currentState.current_stage_index ? currentState.current_stage_color : '#ff4d4f',
    duration_seconds: 300,
  }));

  const totalDuration = stageList.reduce((sum, s) => sum + s.duration_seconds, 0);

  return (
    <div style={{ marginTop: 8, padding: '6px 0' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <Space size={4}>
          <ThunderboltOutlined style={{ color: '#ff4d4f', fontSize: 11 }} />
          <Text style={{ color: '#ffa39e', fontSize: 11, fontWeight: 500 }}>
            {currentState.current_stage_name || 'Attack'}
          </Text>
          {currentState.is_active && !currentState.is_completed && (
            <Text style={{ color: '#6a8caf', fontSize: 10 }}>
              {formatDuration(currentState.stage_remaining_s)} left
            </Text>
          )}
          {currentState.is_completed && (
            <Tag color="green" style={{ fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px' }}>
              Complete
            </Tag>
          )}
          {currentState.is_paused && (
            <Tag color="orange" style={{ fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px' }}>
              Paused
            </Tag>
          )}
          <Tag
            style={{
              fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px',
              background: '#2a1215', borderColor: '#5c2223', color: '#ff7875',
            }}
          >
            {currentState.attack_packets_generated} pkts
          </Tag>
        </Space>
        <Space size={2}>
          {currentState.is_active && !currentState.is_completed && (
            <>
              <Tooltip title={currentState.is_paused ? 'Resume attack' : 'Pause attack'}>
                <Button
                  type="text"
                  size="small"
                  icon={currentState.is_paused ? <PlayCircleOutlined /> : <PauseCircleOutlined />}
                  onClick={handleTogglePause}
                  loading={loading}
                  style={{ fontSize: 11, color: '#ff7875', width: 22, height: 22 }}
                />
              </Tooltip>
              <Tooltip title="Skip to next stage">
                <Button
                  type="text"
                  size="small"
                  icon={<ForwardOutlined />}
                  onClick={handleSkip}
                  loading={loading}
                  style={{ fontSize: 11, color: '#ff7875', width: 22, height: 22 }}
                />
              </Tooltip>
            </>
          )}
          {!currentState.is_active && !currentState.is_completed && (
            <Tooltip title="Start attack">
              <Button
                type="text"
                size="small"
                icon={<ThunderboltOutlined />}
                onClick={handleStart}
                loading={loading}
                style={{ fontSize: 11, color: '#ff7875', width: 22, height: 22 }}
              />
            </Tooltip>
          )}
          {currentState.is_active && (
            <Tooltip title="Stop attack">
              <Button
                type="text"
                size="small"
                danger
                onClick={handleStop}
                loading={loading}
                style={{ fontSize: 11, width: 22, height: 22 }}
              >
                ■
              </Button>
            </Tooltip>
          )}
        </Space>
      </div>

      {/* Timeline bar */}
      <div
        style={{
          display: 'flex',
          height: 12,
          borderRadius: 6,
          overflow: 'hidden',
          background: '#1a0d0d',
          border: '1px solid #5c2223',
        }}
      >
        {stageList.map((s, i) => {
          const widthPct = (s.duration_seconds / totalDuration) * 100;
          const isCurrent = i === currentState.current_stage_index;
          const isPast = i < currentState.current_stage_index ||
            (currentState.is_completed && i <= currentState.current_stage_index);

          return (
            <Tooltip
              key={s.stage_id}
              title={`${s.name} — ${formatDuration(s.duration_seconds)}`}
            >
              <div
                style={{
                  width: `${widthPct}%`,
                  minWidth: 4,
                  background: isPast ? s.color : isCurrent ? `${s.color}cc` : `${s.color}30`,
                  transition: 'background 0.3s ease',
                  position: 'relative',
                  borderRight: i < stageList.length - 1 ? '1px solid #1a0d0d' : undefined,
                }}
              >
                {isCurrent && !currentState.is_completed && (
                  <div
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      height: '100%',
                      width: `${currentState.stage_progress_pct}%`,
                      background: s.color,
                      opacity: 0.6,
                      transition: 'width 1s linear',
                    }}
                  />
                )}
              </div>
            </Tooltip>
          );
        })}
      </div>

      {/* Stage names */}
      <div style={{ display: 'flex', marginTop: 2 }}>
        {stageList.map((s, i) => {
          const widthPct = (s.duration_seconds / totalDuration) * 100;
          const isCurrent = i === currentState.current_stage_index;

          return (
            <div
              key={s.stage_id}
              style={{
                width: `${widthPct}%`,
                minWidth: 4,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontSize: 9,
                color: isCurrent ? '#ffa39e' : '#5c2223',
                fontWeight: isCurrent ? 600 : 400,
                textAlign: 'center',
                paddingTop: 1,
              }}
            >
              {widthPct > 12 ? s.name : ''}
            </div>
          );
        })}
      </div>

      {/* Pulse animation */}
      <style>{`
        @keyframes attack-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
};

export default KillChainTimeline;
