/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Timeline editor for scenario phases
 * Bottom panel with draggable/resizable phase blocks
 */

import React, { useState, useRef, useEffect } from 'react';
import { Typography, Button, Tooltip } from 'antd';
import { PlusOutlined, CloseOutlined } from '@ant-design/icons';
import { useScenarioStore } from '../../stores/scenarioStore';
import type { Phase } from '../../types';

const { Text } = Typography;

const PHASE_COLORS: Record<string, string> = {
  startup: '#52c41a',
  'steady-state': '#1890ff',
  maintenance: '#faad14',
  shutdown: '#fa8c16',
  custom: '#722ed1',
};

interface PhaseBlockProps {
  phase: Phase;
  totalDuration: number;
  onUpdate: (id: string, updates: Partial<Phase>) => void;
  onDelete: (id: string) => void;
}

const PhaseBlock: React.FC<PhaseBlockProps> = ({ phase, totalDuration, onUpdate, onDelete }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const blockRef = useRef<HTMLDivElement>(null);

  const leftPercent = (phase.startOffsetMs / totalDuration) * 100;
  const widthPercent = (phase.durationMs / totalDuration) * 100;

  const handleMouseDown = (e: React.MouseEvent, mode: 'drag' | 'resize') => {
    e.stopPropagation();
    if (mode === 'drag') {
      setIsDragging(true);
    } else {
      setIsResizing(true);
    }
  };

  useEffect(() => {
    if (!isDragging && !isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!blockRef.current?.parentElement) return;

      const container = blockRef.current.parentElement;
      const containerRect = container.getBoundingClientRect();
      const relativeX = e.clientX - containerRect.left;
      const percentX = (relativeX / containerRect.width) * 100;
      const newOffsetMs = (percentX / 100) * totalDuration;

      if (isDragging) {
        const clampedOffset = Math.max(0, Math.min(newOffsetMs - phase.durationMs / 2, totalDuration - phase.durationMs));
        onUpdate(phase.id, { startOffsetMs: Math.round(clampedOffset) });
      } else if (isResizing) {
        const newDuration = newOffsetMs - phase.startOffsetMs;
        const clampedDuration = Math.max(1000, Math.min(newDuration, totalDuration - phase.startOffsetMs));
        onUpdate(phase.id, { durationMs: Math.round(clampedDuration) });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setIsResizing(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, isResizing, phase, totalDuration, onUpdate]);

  return (
    <div
      ref={blockRef}
      style={{
        position: 'absolute',
        left: `${leftPercent}%`,
        width: `${widthPercent}%`,
        height: '60px',
        background: phase.color || PHASE_COLORS[phase.name] || PHASE_COLORS.custom,
        borderRadius: '4px',
        border: '2px solid rgba(0, 0, 0, 0.1)',
        cursor: isDragging ? 'grabbing' : 'grab',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px',
        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
        transition: isDragging || isResizing ? 'none' : 'all 0.2s ease',
      }}
      onMouseDown={(e) => handleMouseDown(e, 'drag')}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            color: 'white',
            fontWeight: 600,
            fontSize: '12px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {phase.displayName}
        </div>
        <div
          style={{
            color: 'rgba(255, 255, 255, 0.9)',
            fontSize: '10px',
          }}
        >
          {(phase.durationMs / 1000).toFixed(1)}s
        </div>
      </div>
      <Tooltip title="Delete phase">
        <Button
          type="text"
          size="small"
          icon={<CloseOutlined style={{ color: 'white' }} />}
          onClick={(e) => {
            e.stopPropagation();
            onDelete(phase.id);
          }}
          style={{
            padding: '4px',
            minWidth: 'auto',
            height: 'auto',
          }}
        />
      </Tooltip>
      <div
        style={{
          position: 'absolute',
          right: 0,
          top: 0,
          bottom: 0,
          width: '8px',
          cursor: 'ew-resize',
          background: 'rgba(255, 255, 255, 0.3)',
          borderTopRightRadius: '4px',
          borderBottomRightRadius: '4px',
        }}
        onMouseDown={(e) => handleMouseDown(e, 'resize')}
      />
    </div>
  );
};

const TimelineEditor: React.FC = () => {
  const phases = useScenarioStore((state) => state.phases);
  const totalDurationMs = useScenarioStore((state) => state.totalDurationMs);
  const updatePhase = useScenarioStore((state) => state.updatePhase);
  const removePhase = useScenarioStore((state) => state.removePhase);
  const addPhase = useScenarioStore((state) => state.addPhase);

  const handleAddPhase = () => {
    const newPhase: Phase = {
      id: `phase-${Date.now()}`,
      name: 'custom',
      displayName: 'New Phase',
      startOffsetMs: totalDurationMs / 2,
      durationMs: 30000,
      intensity: 1.0,
      color: PHASE_COLORS.custom,
    };
    addPhase(newPhase);
  };

  // Generate time ruler marks
  const timeMarks = [];
  const numMarks = 10;
  for (let i = 0; i <= numMarks; i++) {
    const timeMs = (totalDurationMs / numMarks) * i;
    const timeSec = timeMs / 1000;
    timeMarks.push(
      <div
        key={i}
        style={{
          position: 'absolute',
          left: `${(i / numMarks) * 100}%`,
          top: 0,
          bottom: 0,
          borderLeft: '1px solid #2a3f54',
          paddingLeft: '4px',
          paddingTop: '4px',
        }}
      >
        <Text style={{ fontSize: '10px', color: '#6b6b8a' }}>
          {timeSec.toFixed(0)}s
        </Text>
      </div>
    );
  }

  return (
    <div
      style={{
        width: '100%',
        height: '200px',
        background: '#1a2734',
        borderTop: '1px solid #2a3f54',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #2a3f54',
          background: '#253545',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Text strong style={{ fontSize: '14px', color: '#e0e8f0' }}>
          Timeline
        </Text>
        <Button
          type="primary"
          size="small"
          icon={<PlusOutlined />}
          onClick={handleAddPhase}
        >
          Add Phase
        </Button>
      </div>

      {/* Timeline ruler */}
      <div
        style={{
          position: 'relative',
          height: '30px',
          background: '#1e3040',
          borderBottom: '1px solid #2a3f54',
        }}
      >
        {timeMarks}
      </div>

      {/* Phase blocks */}
      <div
        style={{
          position: 'relative',
          flex: 1,
          background: '#1a2734',
          padding: '16px',
        }}
      >
        {phases.map((phase) => (
          <PhaseBlock
            key={phase.id}
            phase={phase}
            totalDuration={totalDurationMs}
            onUpdate={updatePhase}
            onDelete={removePhase}
          />
        ))}
      </div>
    </div>
  );
};

export default TimelineEditor;
