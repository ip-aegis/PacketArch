/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 Verify workspace panel — the ONE place that answers "is my
 * scenario right?". Conduit compliance, architecture rationality, deploy
 * readiness, and AI review render as a single severity-sorted findings
 * list. Hovering a finding spotlights the affected elements on the
 * canvas; clicking zooms to them; AI findings offer one-click fixes.
 */

import React, { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { message } from 'antd';
import { useDocumentStore } from '../document/documentStore';
import { useHealthStore, useHealth } from '../health/healthStore';
import { SOURCE_LABELS, type HealthFinding } from '../health/health';
import { useStudio2UI } from '../uiState';
import { useFeatures } from '../../hooks/useFeatures';
import { SURFACE, TEXT, STATUS, ACCENT, ACCENT_SOFT, FONT, type StatusLevel } from '../tokens';

const PANEL_WIDTH = 340;

const sevColor: Record<HealthFinding['severity'], string> = {
  crit: STATUS.crit,
  warn: STATUS.warn,
  info: TEXT.faint,
};

const actionButton: React.CSSProperties = {
  background: SURFACE.raised,
  border: `1px solid ${SURFACE.border}`,
  borderRadius: 6,
  color: TEXT.secondary,
  fontFamily: FONT.ui,
  fontSize: 11.5,
  fontWeight: 600,
  padding: '4px 10px',
  cursor: 'pointer',
};

const FindingRow: React.FC<{ finding: HealthFinding; scenarioId: string }> = ({
  finding,
  scenarioId,
}) => {
  const setHighlight = useStudio2UI((s) => s.setHighlight);
  const setFocusRequest = useStudio2UI((s) => s.setFocusRequest);
  const remediating = useHealthStore((s) => s.remediating);
  const queryClient = useQueryClient();
  const hasTargets = finding.deviceIds.length > 0 || finding.flowIds.length > 0;

  const applyFix = async () => {
    if (!finding.remediation) return;
    const ok = await useHealthStore.getState().remediate(scenarioId, [finding.remediation]);
    if (ok) {
      message.success('Fix applied');
      await queryClient.invalidateQueries({ queryKey: ['scenario', scenarioId] });
      void useHealthStore.getState().runReview(scenarioId);
    } else {
      message.error('Fix failed');
    }
  };

  return (
    <div
      onMouseEnter={() =>
        hasTargets && setHighlight({ nodeIds: finding.deviceIds, edgeIds: finding.flowIds })
      }
      onMouseLeave={() => setHighlight(null)}
      onClick={() =>
        hasTargets && setFocusRequest({ nodeIds: finding.deviceIds, edgeIds: finding.flowIds })
      }
      role={hasTargets ? 'button' : undefined}
      tabIndex={hasTargets ? 0 : undefined}
      style={{
        display: 'grid',
        gridTemplateColumns: '10px 1fr',
        gap: 9,
        padding: '9px 10px',
        borderRadius: 8,
        cursor: hasTargets ? 'pointer' : 'default',
        border: `1px solid transparent`,
        transition: 'background 100ms ease',
      }}
      onFocus={(e) => (e.currentTarget.style.background = SURFACE.hover)}
      onBlur={(e) => (e.currentTarget.style.background = 'transparent')}
      onMouseOver={(e) => (e.currentTarget.style.background = SURFACE.hover)}
      onMouseOut={(e) => (e.currentTarget.style.background = 'transparent')}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: sevColor[finding.severity],
          marginTop: 5,
        }}
      />
      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
          <span style={{ fontSize: 12.5, fontWeight: 600, color: TEXT.primary, lineHeight: 1.35 }}>
            {finding.title}
          </span>
        </div>
        {finding.detail && (
          <div style={{ fontSize: 11.5, color: TEXT.muted, lineHeight: 1.45, marginTop: 2 }}>
            {finding.detail}
          </div>
        )}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 4 }}>
          <span
            style={{
              fontFamily: FONT.mono,
              fontSize: 9,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: TEXT.faint,
            }}
          >
            {SOURCE_LABELS[finding.source]}
          </span>
          {finding.remediation && (
            <button
              style={{ ...actionButton, padding: '1px 8px', fontSize: 10.5 }}
              disabled={remediating}
              onClick={(e) => {
                e.stopPropagation();
                void applyFix();
              }}
            >
              Fix
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const HealthPanel: React.FC = () => {
  const scenarioId = useDocumentStore((s) => s.doc?.meta.id ?? null);
  const { findings, score, counts } = useHealth();
  const validationLoading = useHealthStore((s) => s.validationLoading);
  const review = useHealthStore((s) => s.review);
  const reviewLoading = useHealthStore((s) => s.reviewLoading);
  const reviewError = useHealthStore((s) => s.reviewError);
  const remediating = useHealthStore((s) => s.remediating);
  const { aiEnabled } = useFeatures();
  const queryClient = useQueryClient();

  // Backend validation runs automatically when Verify opens
  useEffect(() => {
    if (scenarioId) void useHealthStore.getState().runValidation(scenarioId);
  }, [scenarioId]);

  if (!scenarioId) return null;

  const scoreStatus: StatusLevel = score >= 85 ? 'ok' : score >= 60 ? 'warn' : 'crit';
  const fixable = findings.filter((f) => f.remediation);

  const fixAll = async () => {
    const ok = await useHealthStore
      .getState()
      .remediate(scenarioId, fixable.map((f) => f.remediation!));
    if (ok) {
      message.success(`Applied ${fixable.length} fixes`);
      await queryClient.invalidateQueries({ queryKey: ['scenario', scenarioId] });
      void useHealthStore.getState().runReview(scenarioId);
      void useHealthStore.getState().runValidation(scenarioId);
    } else {
      message.error('Fix all failed');
    }
  };

  return (
    <div
      style={{
        width: PANEL_WIDTH,
        flex: `0 0 ${PANEL_WIDTH}px`,
        display: 'flex',
        flexDirection: 'column',
        background: SURFACE.chrome,
        borderLeft: `1px solid ${SURFACE.border}`,
        fontFamily: FONT.ui,
        minHeight: 0,
      }}
    >
      {/* Score header */}
      <div style={{ padding: '14px 16px 10px', borderBottom: `1px solid ${SURFACE.border}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span
            style={{
              fontSize: 30,
              fontWeight: 650,
              color: STATUS[scoreStatus],
              fontVariantNumeric: 'tabular-nums',
              lineHeight: 1,
            }}
          >
            {score}
          </span>
          <div style={{ fontFamily: FONT.mono, fontSize: 10.5, color: TEXT.muted, lineHeight: 1.6 }}>
            <span style={{ color: STATUS.crit }}>{counts.crit} critical</span>
            {' · '}
            <span style={{ color: STATUS.warn }}>{counts.warn} warnings</span>
            {' · '}
            {counts.info} notes
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 12, flexWrap: 'wrap' }}>
          <button
            style={actionButton}
            disabled={validationLoading}
            onClick={() => void useHealthStore.getState().runValidation(scenarioId)}
          >
            {validationLoading ? 'Checking…' : 'Re-run checks'}
          </button>
          {aiEnabled && (
            <button
              style={{ ...actionButton, borderColor: ACCENT, color: ACCENT, background: ACCENT_SOFT }}
              disabled={reviewLoading}
              onClick={() => void useHealthStore.getState().runReview(scenarioId)}
            >
              {reviewLoading ? 'Reviewing…' : review ? 'Re-run AI review' : 'Run AI review'}
            </button>
          )}
          {fixable.length > 0 && (
            <button style={actionButton} disabled={remediating} onClick={() => void fixAll()}>
              {remediating ? 'Fixing…' : `Fix all (${fixable.length})`}
            </button>
          )}
        </div>
        {reviewError && (
          <div style={{ fontSize: 11, color: STATUS.crit, marginTop: 8 }}>{reviewError}</div>
        )}
        {review?.summary && (
          <div style={{ fontSize: 11.5, color: TEXT.muted, marginTop: 8, lineHeight: 1.5 }}>
            {review.summary}
          </div>
        )}
      </div>

      {/* Findings */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 6px' }}>
        {findings.length === 0 ? (
          <div style={{ padding: '18px 12px', fontSize: 12.5, color: TEXT.muted, lineHeight: 1.6 }}>
            No findings — conduits and architecture look clean.
            {aiEnabled && !review ? ' Run the AI review for a deeper pass.' : ''}
          </div>
        ) : (
          findings.map((f) => <FindingRow key={f.id} finding={f} scenarioId={scenarioId} />)
        )}
      </div>

      <div
        style={{
          padding: '8px 16px',
          borderTop: `1px solid ${SURFACE.border}`,
          fontSize: 10.5,
          color: TEXT.faint,
          lineHeight: 1.5,
        }}
      >
        Hover a finding to spotlight it on the canvas; click to zoom to it.
      </div>
    </div>
  );
};

export default HealthPanel;
