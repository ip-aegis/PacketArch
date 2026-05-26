/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * KillChainTimeline - Live attack kill-chain progress visualization.
 * Modeled on PhaseTimeline but with red-tinted attack styling.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Space, Tag, Tooltip, Typography } from 'antd';
import {
  ForwardOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { attacksApi } from '../../api/attacks';
import type { ActionReport, AttackState, StageReport } from '../../types/attackPlaybook';
import AttackIpMatrix from './AttackIpMatrix';

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

  // --- Client-side interpolation for smooth 1s countdown ---
  const lastServerUpdate = useRef<{ time: number; remaining: number; progress: number; stageIdx: number } | null>(null);
  const [displayRemaining, setDisplayRemaining] = useState<number>(0);
  const [displayProgress, setDisplayProgress] = useState<number>(0);

  // Sync from server state whenever it changes
  useEffect(() => {
    if (!currentState?.is_active || currentState.is_completed || currentState.is_paused) return;
    const serverRemaining = currentState.stage_remaining_s;
    const serverProgress = currentState.stage_progress_pct;
    lastServerUpdate.current = {
      time: Date.now(),
      remaining: serverRemaining,
      progress: serverProgress,
      stageIdx: currentState.current_stage_index,
    };
    setDisplayRemaining(serverRemaining);
    setDisplayProgress(serverProgress);
  }, [currentState?.stage_remaining_s, currentState?.stage_progress_pct, currentState?.current_stage_index, currentState?.is_active, currentState?.is_completed, currentState?.is_paused]);

  // 1s local timer to interpolate between server updates
  useEffect(() => {
    if (!currentState?.is_active || currentState.is_completed || currentState.is_paused) return;
    const timer = setInterval(() => {
      const ref = lastServerUpdate.current;
      if (!ref) return;
      const elapsedSinceUpdate = (Date.now() - ref.time) / 1000;
      const interpolatedRemaining = Math.max(0, ref.remaining - elapsedSinceUpdate);
      setDisplayRemaining(interpolatedRemaining);
      // Interpolate progress: advance proportionally
      const totalDuration = ref.remaining / Math.max(0.01, (100 - ref.progress) / 100);
      const interpolatedProgress = totalDuration > 0
        ? Math.min(100, ref.progress + (elapsedSinceUpdate / totalDuration) * 100)
        : ref.progress;
      setDisplayProgress(interpolatedProgress);
    }, 1000);
    return () => clearInterval(timer);
  }, [currentState?.is_active, currentState?.is_completed, currentState?.is_paused]);

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

  // ── Action-level data (from the embedded report) ──────────────────
  // The orchestrator's report rides alongside live state. Each stage
  // carries its action list with fire counts, packet counts, target
  // hits, and fired_at timestamps. We use this for:
  //   - Action dots inside the current stage segment
  //   - The live "recent actions" stream below the timeline
  const report = currentState.report;
  const currentStageReport: StageReport | undefined =
    report?.stages?.[currentState.current_stage_index];
  const currentStageActions: ActionReport[] = currentStageReport?.actions ?? [];

  // Flat list of every action that's fired, sorted newest-first.
  // Capped at 5 entries for the sidebar — full history lives in the
  // after-action report modal.
  const recentActions: Array<ActionReport & { stageName: string; stageColor: string }> =
    (report?.stages ?? [])
      .flatMap((s) =>
        s.actions
          .filter((a) => a.fire_count > 0)
          .map((a) => ({ ...a, stageName: s.stage_name, stageColor: s.color })),
      )
      .sort((a, b) => b.fired_at - a.fired_at)
      .slice(0, 5);

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
              {formatDuration(displayRemaining)} left
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
                      width: `${displayProgress}%`,
                      background: s.color,
                      opacity: 0.6,
                      transition: 'width 1s linear',
                    }}
                  />
                )}
                {/* Action dots — one per action in the current stage,
                    overlaid on the active segment. Filled = fired,
                    outline = pending. Tiny but high-signal: "I've
                    completed 3 of 7 actions in this stage". */}
                {isCurrent && currentStageActions.length > 0 && currentStageActions.length <= 12 && (
                  <div
                    style={{
                      position: 'absolute',
                      top: '50%',
                      left: 0,
                      right: 0,
                      transform: 'translateY(-50%)',
                      display: 'flex',
                      justifyContent: 'space-evenly',
                      alignItems: 'center',
                      pointerEvents: 'none',
                      paddingInline: 4,
                    }}
                  >
                    {currentStageActions.map((a) => {
                      const fired = a.fire_count > 0;
                      return (
                        <div
                          key={a.action_id}
                          style={{
                            width: 5,
                            height: 5,
                            borderRadius: '50%',
                            background: fired ? '#fff' : 'transparent',
                            border: '1px solid rgba(255,255,255,0.8)',
                            boxShadow: fired
                              ? '0 0 4px rgba(255,255,255,0.9)'
                              : undefined,
                          }}
                        />
                      );
                    })}
                  </div>
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

      {/* Current-stage action progress + recent-action stream. Only
          rendered when the orchestrator's embedded report has data;
          older agents (pre-v1.44) skip this gracefully. */}
      {currentStageReport && currentStageActions.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 4,
            }}
          >
            <Text style={{ color: '#6a8caf', fontSize: 9 }}>
              Stage actions:{' '}
              <span style={{ color: '#ffa39e', fontWeight: 600 }}>
                {currentStageActions.filter((a) => a.fire_count > 0).length}
              </span>
              {' / '}
              {currentStageActions.length}
            </Text>
            {currentStageReport.packets_emitted > 0 && (
              <Text style={{ color: '#6a8caf', fontSize: 9 }}>
                Stage packets:{' '}
                <span style={{ color: '#ffa39e', fontWeight: 600 }}>
                  {currentStageReport.packets_emitted}
                </span>
              </Text>
            )}
          </div>
        </div>
      )}

      {recentActions.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <Text
            style={{
              color: '#8aa4bc',
              fontSize: 9,
              display: 'block',
              marginBottom: 3,
              textTransform: 'uppercase',
              letterSpacing: 0.4,
            }}
          >
            Recent actions
          </Text>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 3,
              maxHeight: 130,
              overflowY: 'auto',
            }}
          >
            {recentActions.map((a) => (
              <Tooltip
                key={`${a.action_id}-${a.fired_at}`}
                title={
                  <div style={{ maxWidth: 280 }}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>
                      {a.action_name}
                    </div>
                    <div style={{ fontSize: 11, color: '#a8a8c0' }}>
                      {a.description || a.action_type}
                    </div>
                    {a.expected_cv_detection && (
                      <div style={{ fontSize: 11, marginTop: 6, color: '#52c41a' }}>
                        CV: {a.expected_cv_detection}
                      </div>
                    )}
                  </div>
                }
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                    padding: '3px 6px',
                    background: '#0d1117',
                    borderRadius: 3,
                    borderLeft: `2px solid ${a.stageColor}`,
                    cursor: 'default',
                  }}
                >
                  <Text
                    style={{
                      color: '#e6f1ff',
                      fontSize: 10,
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {a.action_name}
                  </Text>
                  {a.mitre_technique && (
                    <Tag
                      style={{
                        margin: 0,
                        fontSize: 8,
                        lineHeight: '12px',
                        padding: '0 3px',
                        background: '#1d1d3a',
                        borderColor: '#3d3d7a',
                        color: '#b3b3ff',
                      }}
                    >
                      {a.mitre_technique}
                    </Tag>
                  )}
                  {a.fire_count > 1 && (
                    <Text style={{ color: '#52c41a', fontSize: 9 }}>
                      ×{a.fire_count}
                    </Text>
                  )}
                  <Text style={{ color: '#ff7875', fontSize: 9, minWidth: 32, textAlign: 'right' }}>
                    {a.packets_emitted}p
                  </Text>
                </div>
              </Tooltip>
            ))}
          </div>
        </div>
      )}

      {/* Live IP attack matrix — appears when the report carries at
          least one (attacker, target) pair. Compact for the sidebar;
          the full sortable table lives in the after-action modal. */}
      {report && (
        <div style={{ marginTop: 8 }}>
          <AttackIpMatrix report={report} variant="compact" maxRows={5} />
        </div>
      )}

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
