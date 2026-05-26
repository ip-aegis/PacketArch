/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * KillChainFlowChart — SVG flowchart of a playbook's kill-chain stages.
 *
 * Renders stages as connected rectangles with the stage's colour band,
 * name, duration, and action count. Arrows show progression. Designed
 * for the static documentation context (the Attack Library detail
 * page) — different role from `KillChainTimeline`, which renders the
 * live progress bar during execution.
 *
 * Layout:
 *   - Up to ~6 stages: single horizontal row, scrolls if needed
 *   - Each stage card is fixed-width so the diagram reads consistently
 *   - Stage colour comes from `KillChainStage.color`
 *
 * Click a stage to fire `onStageClick(stage_id)` so the parent page
 * can scroll to the stage's expanded detail.
 */

import React from 'react';
import { Typography } from 'antd';
import type { KillChainStage } from '../../types/attackPlaybook';

const { Text } = Typography;

const CARD_WIDTH = 180;
const CARD_HEIGHT = 110;
const ARROW_WIDTH = 24;
const ROW_GAP = 28;

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export interface KillChainFlowChartProps {
  stages: KillChainStage[];
  onStageClick?: (stageId: string) => void;
}

const KillChainFlowChart: React.FC<KillChainFlowChartProps> = ({
  stages,
  onStageClick,
}) => {
  if (stages.length === 0) return null;

  const totalWidth = stages.length * CARD_WIDTH + (stages.length - 1) * ARROW_WIDTH;
  const totalHeight = CARD_HEIGHT + ROW_GAP;

  return (
    <div
      style={{
        overflowX: 'auto',
        padding: '12px 4px',
        background: '#0d1117',
        borderRadius: 6,
        border: '1px solid #2d2d52',
      }}
    >
      <svg
        width={Math.max(totalWidth, 600)}
        height={totalHeight}
        viewBox={`0 0 ${totalWidth} ${totalHeight}`}
        style={{ display: 'block' }}
      >
        <defs>
          <marker
            id="killchain-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="8"
            markerHeight="8"
            orient="auto"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#5a6b7e" />
          </marker>
        </defs>

        {stages.map((stage, i) => {
          const x = i * (CARD_WIDTH + ARROW_WIDTH);
          const y = ROW_GAP / 2;

          // Arrow into this card (except for the first one)
          const arrow =
            i === 0 ? null : (
              <line
                x1={x - ARROW_WIDTH + 4}
                y1={y + CARD_HEIGHT / 2}
                x2={x - 2}
                y2={y + CARD_HEIGHT / 2}
                stroke="#5a6b7e"
                strokeWidth={2}
                markerEnd="url(#killchain-arrow)"
              />
            );

          const totalActions = stage.actions.length;
          const labelClickable = !!onStageClick;
          return (
            <g key={stage.stage_id}>
              {arrow}
              <g
                style={{ cursor: labelClickable ? 'pointer' : 'default' }}
                onClick={
                  labelClickable
                    ? () => onStageClick!(stage.stage_id)
                    : undefined
                }
              >
                <title>{stage.description || stage.name}</title>
                {/* Card background */}
                <rect
                  x={x}
                  y={y}
                  width={CARD_WIDTH}
                  height={CARD_HEIGHT}
                  rx={6}
                  fill="#141428"
                  stroke={stage.color}
                  strokeWidth={1.5}
                />
                {/* Colour band on left */}
                <rect
                  x={x}
                  y={y}
                  width={4}
                  height={CARD_HEIGHT}
                  rx={2}
                  fill={stage.color}
                />
                {/* Stage index */}
                <circle
                  cx={x + CARD_WIDTH - 18}
                  cy={y + 18}
                  r={11}
                  fill={`${stage.color}66`}
                  stroke={stage.color}
                  strokeWidth={1}
                />
                <text
                  x={x + CARD_WIDTH - 18}
                  y={y + 22}
                  textAnchor="middle"
                  fill="#fff"
                  fontSize={11}
                  fontWeight={600}
                >
                  {i + 1}
                </text>
                {/* Stage name */}
                <foreignObject
                  x={x + 14}
                  y={y + 12}
                  width={CARD_WIDTH - 50}
                  height={48}
                >
                  <div
                    style={{
                      color: '#dde2ec',
                      fontSize: 12,
                      fontWeight: 600,
                      lineHeight: 1.25,
                      overflow: 'hidden',
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                    }}
                  >
                    {stage.name}
                  </div>
                </foreignObject>
                {/* Duration */}
                <text
                  x={x + 14}
                  y={y + CARD_HEIGHT - 28}
                  fill="#8aa4bc"
                  fontSize={10}
                >
                  ⏱ {formatDuration(stage.duration_seconds)}
                </text>
                {/* Action count */}
                <text
                  x={x + 14}
                  y={y + CARD_HEIGHT - 12}
                  fill="#8aa4bc"
                  fontSize={10}
                >
                  ◉ {totalActions} action{totalActions === 1 ? '' : 's'}
                </text>
                {/* MITRE tactic on the right side bottom */}
                {stage.mitre_tactics.length > 0 && (
                  <text
                    x={x + CARD_WIDTH - 8}
                    y={y + CARD_HEIGHT - 12}
                    textAnchor="end"
                    fill={stage.color}
                    fontSize={9}
                    fontFamily="ui-monospace, monospace"
                  >
                    {stage.mitre_tactics[0]}
                  </text>
                )}
              </g>
            </g>
          );
        })}
      </svg>
      {onStageClick && (
        <Text
          type="secondary"
          style={{ fontSize: 11, marginTop: 8, display: 'block', textAlign: 'center' }}
        >
          Click a stage to jump to its detail below
        </Text>
      )}
    </div>
  );
};

export default KillChainFlowChart;
