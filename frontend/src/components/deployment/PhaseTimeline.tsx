/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * PhaseTimeline - Displays deployment phase cycling status
 * with a horizontal timeline bar and phase controls.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { Button, Space, Tag, Tooltip, Typography } from 'antd';
import {
  ForwardOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import { adaptationApi, type PhaseScheduleInfo } from '../../api/adaptation';
import { extractErrorMessage } from '../../utils/errorUtils';

const { Text } = Typography;

interface PhaseTimelineProps {
  scenarioId: string;
  isRunning: boolean;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

const PhaseTimeline: React.FC<PhaseTimelineProps> = ({ scenarioId, isRunning }) => {
  const [phaseInfo, setPhaseInfo] = useState<PhaseScheduleInfo | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchState = useCallback(async () => {
    try {
      const state = await adaptationApi.getState(scenarioId);
      if (state.phase_schedule?.active) {
        setPhaseInfo(state.phase_schedule);
      } else {
        setPhaseInfo(null);
      }
    } catch {
      // Silently ignore — phase info is optional
    }
  }, [scenarioId]);

  // Poll adaptation state while running
  useEffect(() => {
    if (!isRunning) {
      setPhaseInfo(null);
      return;
    }
    fetchState();
    const interval = setInterval(fetchState, 5000);
    return () => clearInterval(interval);
  }, [isRunning, fetchState]);

  const handleSkip = async () => {
    setLoading(true);
    try {
      await adaptationApi.skipPhase(scenarioId);
      await fetchState();
    } catch (err: unknown) {
      console.error(extractErrorMessage(err, 'Failed to skip phase'));
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePause = async () => {
    if (!phaseInfo) return;
    setLoading(true);
    try {
      await adaptationApi.togglePhasePause(scenarioId, !phaseInfo.paused);
      await fetchState();
    } catch (err: unknown) {
      console.error(extractErrorMessage(err, 'Failed to toggle pause'));
    } finally {
      setLoading(false);
    }
  };

  if (!phaseInfo || !phaseInfo.phases || phaseInfo.phases.length === 0) {
    return null;
  }

  const totalDuration = phaseInfo.phases.reduce((sum, p) => sum + p.duration_s, 0);

  return (
    <div style={{ marginTop: 8, padding: '6px 0' }}>
      {/* Phase label + controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <Space size={4}>
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: phaseInfo.color ?? '#1890ff',
              animation: phaseInfo.paused ? 'none' : 'pulse 2s infinite',
            }}
          />
          <Text style={{ color: '#e6f1ff', fontSize: 11, fontWeight: 500 }}>
            {phaseInfo.name}
          </Text>
          <Text style={{ color: '#6a8caf', fontSize: 10 }}>
            {formatDuration(phaseInfo.remaining_s ?? 0)} left
          </Text>
          {(phaseInfo.cycle_count ?? 0) > 0 && (
            <Tag color="blue" style={{ fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px' }}>
              Cycle {(phaseInfo.cycle_count ?? 0) + 1}
            </Tag>
          )}
          {phaseInfo.paused && (
            <Tag color="orange" style={{ fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px' }}>
              Paused
            </Tag>
          )}
          {phaseInfo.forced && (
            <Tag color="purple" style={{ fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px' }}>
              Forced
            </Tag>
          )}
        </Space>
        <Space size={2}>
          <Tooltip title={phaseInfo.paused ? 'Resume cycling' : 'Pause cycling'}>
            <Button
              type="text"
              size="small"
              icon={phaseInfo.paused ? <PlayCircleOutlined /> : <PauseCircleOutlined />}
              onClick={handleTogglePause}
              loading={loading}
              style={{ fontSize: 11, color: '#8aa4bc', width: 22, height: 22 }}
            />
          </Tooltip>
          <Tooltip title="Skip to next phase">
            <Button
              type="text"
              size="small"
              icon={<ForwardOutlined />}
              onClick={handleSkip}
              loading={loading}
              style={{ fontSize: 11, color: '#8aa4bc', width: 22, height: 22 }}
            />
          </Tooltip>
        </Space>
      </div>

      {/* Timeline bar */}
      <div
        style={{
          display: 'flex',
          height: 12,
          borderRadius: 6,
          overflow: 'hidden',
          background: '#0d1b2a',
          border: '1px solid #2a3f54',
        }}
      >
        {phaseInfo.phases.map((p, i) => {
          const widthPct = (p.duration_s / totalDuration) * 100;
          const isCurrent = i === phaseInfo.phase_index;

          return (
            <Tooltip
              key={p.phase_id}
              title={`${p.name} — ${formatDuration(p.duration_s)} (${Math.round(p.rate_multiplier * 100)}% rate)`}
            >
              <div
                style={{
                  width: `${widthPct}%`,
                  minWidth: 4,
                  background: isCurrent ? p.color : `${p.color}40`,
                  transition: 'background 0.3s ease',
                  position: 'relative',
                  borderRight: i < phaseInfo.phases!.length - 1 ? '1px solid #0d1b2a' : undefined,
                }}
              >
                {/* Progress fill within current phase */}
                {isCurrent && (
                  <div
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      height: '100%',
                      width: `${phaseInfo.progress_pct ?? 0}%`,
                      background: p.color,
                      opacity: 0.5,
                      transition: 'width 1s linear',
                    }}
                  />
                )}
              </div>
            </Tooltip>
          );
        })}
      </div>

      {/* Phase names below timeline */}
      <div style={{ display: 'flex', marginTop: 2 }}>
        {phaseInfo.phases.map((p, i) => {
          const widthPct = (p.duration_s / totalDuration) * 100;
          const isCurrent = i === phaseInfo.phase_index;

          return (
            <div
              key={p.phase_id}
              style={{
                width: `${widthPct}%`,
                minWidth: 4,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontSize: 9,
                color: isCurrent ? '#e6f1ff' : '#4a6a8a',
                fontWeight: isCurrent ? 600 : 400,
                textAlign: 'center',
                paddingTop: 1,
              }}
            >
              {widthPct > 12 ? p.name : ''}
            </div>
          );
        })}
      </div>

      {/* CSS animation for pulse */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
};

export default PhaseTimeline;
