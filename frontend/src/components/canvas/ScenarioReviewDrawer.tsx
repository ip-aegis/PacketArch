/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Scenario Review Drawer - AI-powered scenario quality analysis with categorized findings
 * and one-click remediation for fixable issues.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Drawer,
  Collapse,
  Tag,
  Button,
  Space,
  Typography,
  Empty,
  Spin,
  Alert,
  App,
  Tooltip,
} from 'antd';
import {
  ClusterOutlined,
  ApiOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  SafetyOutlined,
  BulbOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ToolOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import {
  aiApi,
  type ReviewFinding,
  type ScenarioReviewResponse,
  type RemediationAction,
} from '../../api/ai';
import scenariosApi from '../../api/scenarios';
import { useScenarioStore } from '../../stores/scenarioStore';
import { extractErrorMessage } from '../../utils/errorUtils';
import type { ScenarioDevice, ScenarioFlow, ScenarioZone, Phase } from '../../types';

const { Text, Title } = Typography;

interface ScenarioReviewDrawerProps {
  scenarioId: string | null;
  open: boolean;
  onClose: () => void;
}

const SEVERITY_CONFIG: Record<string, { color: string; label: string }> = {
  critical: { color: '#ff4d4f', label: 'Critical' },
  warning: { color: '#faad14', label: 'Warning' },
  suggestion: { color: '#1890ff', label: 'Suggestion' },
  info: { color: '#52c41a', label: 'Info' },
};

const CATEGORY_CONFIG: Record<string, { icon: React.ReactNode; label: string }> = {
  topology: { icon: <ClusterOutlined />, label: 'Topology' },
  protocols: { icon: <ApiOutlined />, label: 'Protocols' },
  timing: { icon: <ClockCircleOutlined />, label: 'Timing' },
  realism: { icon: <ExperimentOutlined />, label: 'Realism' },
  security: { icon: <SafetyOutlined />, label: 'Security' },
};

const CATEGORY_ORDER = ['topology', 'protocols', 'timing', 'realism', 'security'];

function getScoreColor(score: number): string {
  if (score >= 80) return '#52c41a';
  if (score >= 60) return '#faad14';
  return '#ff4d4f';
}

interface FindingCardProps {
  finding: ReviewFinding;
  isFixing: boolean;
  isFixed: boolean;
  failMessage: string | null;
  onFix: () => void;
}

function FindingCard({ finding, isFixing, isFixed, failMessage, onFix }: FindingCardProps) {
  const sev = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.info;

  return (
    <div
      style={{
        background: isFixed ? '#142214' : '#141428',
        borderRadius: 6,
        padding: '10px 14px',
        borderLeft: `3px solid ${isFixed ? '#52c41a' : sev.color}`,
        marginBottom: 8,
        opacity: isFixed ? 0.7 : 1,
        transition: 'all 0.3s ease',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Text
          strong
          style={{
            color: isFixed ? '#52c41a' : '#e0e0f0',
            fontSize: 13,
            display: 'block',
            marginBottom: 4,
            flex: 1,
          }}
        >
          {isFixed && <CheckCircleOutlined style={{ marginRight: 6 }} />}
          {finding.title}
        </Text>
        {finding.remediation && !isFixed && (
          <Button
            type="primary"
            size="small"
            icon={isFixing ? <LoadingOutlined /> : <ToolOutlined />}
            onClick={onFix}
            loading={isFixing}
            style={{
              marginLeft: 8,
              flexShrink: 0,
              background: '#1890ff',
              borderColor: '#1890ff',
            }}
          >
            Fix
          </Button>
        )}
      </div>
      <Text style={{ color: '#b8c9dc', fontSize: 12, display: 'block', marginBottom: 6 }}>
        {finding.description}
      </Text>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 6,
          color: '#6ba3d6',
          fontSize: 12,
        }}
      >
        <BulbOutlined style={{ marginTop: 2, flexShrink: 0 }} />
        <span>{finding.suggestion}</span>
      </div>
      {failMessage && (
        <Text style={{ color: '#ff4d4f', fontSize: 11, display: 'block', marginTop: 4 }}>
          Fix failed: {failMessage}
        </Text>
      )}
    </div>
  );
}

const ScenarioReviewDrawer: React.FC<ScenarioReviewDrawerProps> = ({
  scenarioId,
  open,
  onClose,
}) => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [reviewData, setReviewData] = useState<ScenarioReviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fix state
  const [fixingIndices, setFixingIndices] = useState<Set<number>>(new Set());
  const [fixedIndices, setFixedIndices] = useState<Set<number>>(new Set());
  const [failedIndices, setFailedIndices] = useState<Map<number, string>>(new Map());
  const [fixAllLoading, setFixAllLoading] = useState(false);
  const [previousScore, setPreviousScore] = useState<number | null>(null);

  const reloadScenario = useCallback(async () => {
    if (!scenarioId) return;
    try {
      await new Promise((resolve) => setTimeout(resolve, 200));
      const scenario = await scenariosApi.get(scenarioId);
      const definition = scenario.definition as {
        devices?: Record<string, unknown>;
        flows?: Record<string, unknown>;
        zones?: Record<string, unknown>;
        phases?: unknown[];
      };
      useScenarioStore.getState().loadScenario({
        id: scenario.id,
        name: scenario.name,
        description: scenario.description || '',
        vertical: scenario.vertical || undefined,
        totalDurationMs: scenario.total_duration_ms,
        devices: (definition?.devices || {}) as Record<string, ScenarioDevice>,
        flows: (definition?.flows || {}) as Record<string, ScenarioFlow>,
        zones: (definition?.zones || {}) as Record<string, ScenarioZone>,
        phases: (definition?.phases || []) as Phase[],
        addressingConfig: scenario.addressing_config as {
          ip_range?: string;
          range_index?: number;
          auto_assign_enabled?: boolean;
        } | null,
      });
    } catch (err) {
      console.error('Failed to reload scenario after remediation:', err);
    }
  }, [scenarioId]);

  const fetchReview = useCallback(async () => {
    if (!scenarioId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await aiApi.reviewScenario(scenarioId);
      setReviewData(data);
    } catch (err: unknown) {
      const msg = extractErrorMessage(err, 'Failed to review scenario');
      setError(msg);
      message.error(msg);
    } finally {
      setLoading(false);
    }
  }, [scenarioId, message]);

  useEffect(() => {
    if (open && scenarioId && !reviewData && !loading) {
      fetchReview();
    }
  }, [open, scenarioId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRerun = () => {
    if (reviewData) {
      setPreviousScore(reviewData.overall_score);
    }
    setReviewData(null);
    resetFixState();
    fetchReview();
  };

  const resetFixState = () => {
    setFixingIndices(new Set());
    setFixedIndices(new Set());
    setFailedIndices(new Map());
    setFixAllLoading(false);
  };

  // Reset state when drawer closes
  useEffect(() => {
    if (!open) {
      setReviewData(null);
      setError(null);
      setPreviousScore(null);
      resetFixState();
    }
  }, [open]);

  const handleFixSingle = useCallback(
    async (findingIndex: number) => {
      if (!scenarioId || !reviewData) return;
      const finding = reviewData.findings[findingIndex];
      if (!finding?.remediation) return;

      setFixingIndices((prev) => new Set(prev).add(findingIndex));
      setFailedIndices((prev) => {
        const next = new Map(prev);
        next.delete(findingIndex);
        return next;
      });

      try {
        const resp = await aiApi.remediateScenario(scenarioId, [finding.remediation]);
        const result = resp.results[0];
        if (result?.success) {
          setFixedIndices((prev) => new Set(prev).add(findingIndex));
          message.success(result.message);
          await reloadScenario();
        } else {
          setFailedIndices((prev) => new Map(prev).set(findingIndex, result?.message || 'Unknown error'));
          message.error(result?.message || 'Fix failed');
        }
      } catch (err: unknown) {
        const msg = extractErrorMessage(err, 'Fix failed');
        setFailedIndices((prev) => new Map(prev).set(findingIndex, msg));
        message.error(msg);
      } finally {
        setFixingIndices((prev) => {
          const next = new Set(prev);
          next.delete(findingIndex);
          return next;
        });
      }
    },
    [scenarioId, reviewData, message, reloadScenario]
  );

  const handleFixAll = useCallback(async () => {
    if (!scenarioId || !reviewData) return;

    // Collect unfixed findings with remediation actions
    const fixable: { index: number; action: RemediationAction }[] = [];
    reviewData.findings.forEach((f, i) => {
      if (f.remediation && !fixedIndices.has(i)) {
        fixable.push({ index: i, action: f.remediation });
      }
    });

    if (fixable.length === 0) return;

    setFixAllLoading(true);
    const allFixing = new Set(fixable.map((f) => f.index));
    setFixingIndices(allFixing);

    try {
      const resp = await aiApi.remediateScenario(
        scenarioId,
        fixable.map((f) => f.action)
      );

      const newFixed = new Set(fixedIndices);
      const newFailed = new Map(failedIndices);

      resp.results.forEach((result, i) => {
        const findingIndex = fixable[i].index;
        if (result.success) {
          newFixed.add(findingIndex);
          newFailed.delete(findingIndex);
        } else {
          newFailed.set(findingIndex, result.message);
        }
      });

      setFixedIndices(newFixed);
      setFailedIndices(newFailed);

      if (resp.applied > 0) {
        message.success(`Fixed ${resp.applied} issue${resp.applied > 1 ? 's' : ''}`);
        await reloadScenario();
        // Auto re-run review after fixes
        setTimeout(() => {
          if (reviewData) {
            setPreviousScore(reviewData.overall_score);
          }
          setReviewData(null);
          resetFixState();
          fetchReview();
        }, 500);
      }
      if (resp.failed > 0) {
        message.warning(`${resp.failed} fix${resp.failed > 1 ? 'es' : ''} failed`);
      }
    } catch (err: unknown) {
      const msg = extractErrorMessage(err, 'Fix All failed');
      message.error(msg);
    } finally {
      setFixingIndices(new Set());
      setFixAllLoading(false);
    }
  }, [scenarioId, reviewData, fixedIndices, failedIndices, message, reloadScenario, fetchReview]);

  // Count fixable findings
  const fixableCount = reviewData
    ? reviewData.findings.filter((f, i) => f.remediation && !fixedIndices.has(i)).length
    : 0;

  // Group findings by category
  const findingsByCategory: Record<string, { finding: ReviewFinding; globalIndex: number }[]> = {};
  if (reviewData) {
    reviewData.findings.forEach((f, i) => {
      if (!findingsByCategory[f.category]) {
        findingsByCategory[f.category] = [];
      }
      findingsByCategory[f.category].push({ finding: f, globalIndex: i });
    });
  }

  // Build collapse items for categories that have findings
  const collapseItems = CATEGORY_ORDER
    .filter((cat) => findingsByCategory[cat]?.length)
    .map((cat) => {
      const cfg = CATEGORY_CONFIG[cat] || { icon: null, label: cat };
      const entries = findingsByCategory[cat];
      return {
        key: cat,
        label: (
          <Space>
            <span style={{ color: '#b8c9dc' }}>{cfg.icon}</span>
            <Text style={{ color: '#e0e0f0', fontWeight: 500 }}>{cfg.label}</Text>
            <Tag color="default" style={{ marginLeft: 4 }}>
              {entries.length}
            </Tag>
          </Space>
        ),
        children: (
          <div>
            {entries.map(({ finding, globalIndex }) => (
              <FindingCard
                key={`${cat}-${globalIndex}`}
                finding={finding}
                isFixing={fixingIndices.has(globalIndex)}
                isFixed={fixedIndices.has(globalIndex)}
                failMessage={failedIndices.get(globalIndex) ?? null}
                onFix={() => handleFixSingle(globalIndex)}
              />
            ))}
          </div>
        ),
      };
    });

  // Score delta indicator
  const scoreDelta =
    previousScore !== null && reviewData ? reviewData.overall_score - previousScore : null;

  return (
    <Drawer
      title="AI Scenario Review"
      placement="right"
      width={520}
      onClose={onClose}
      open={open}
      styles={{
        header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
        body: { background: '#1a1a2e', padding: '16px' },
        content: { background: '#141428' },
      }}
      extra={
        reviewData && !loading ? (
          <Space>
            {fixableCount > 0 && (
              <Tooltip title="Apply all auto-fixable remediations">
                <Button
                  type="primary"
                  icon={<ToolOutlined />}
                  onClick={handleFixAll}
                  loading={fixAllLoading}
                  size="small"
                >
                  Fix All ({fixableCount})
                </Button>
              </Tooltip>
            )}
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRerun}
              size="small"
              style={{ color: '#b8c9dc', borderColor: '#3a5068' }}
            >
              Re-run
            </Button>
          </Space>
        ) : undefined
      }
    >
      {/* Loading state */}
      {loading && (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
          <div style={{ color: '#6b6b8a', marginTop: 16 }}>Analyzing scenario...</div>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <Alert
          message="Review Failed"
          description={error}
          type="error"
          showIcon
          action={
            <Button size="small" onClick={handleRerun}>
              Retry
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Results */}
      {reviewData && !loading && (
        <>
          {/* Score card */}
          <div
            style={{
              background: '#253545',
              borderRadius: 8,
              padding: '16px 20px',
              marginBottom: 16,
              display: 'flex',
              alignItems: 'center',
              gap: 20,
            }}
          >
            <div style={{ textAlign: 'center' }}>
              <div
                style={{
                  fontSize: 36,
                  fontWeight: 700,
                  color: getScoreColor(reviewData.overall_score),
                  lineHeight: 1,
                }}
              >
                {reviewData.overall_score}
              </div>
              {scoreDelta !== null && scoreDelta !== 0 && (
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: scoreDelta > 0 ? '#52c41a' : '#ff4d4f',
                    marginTop: 2,
                  }}
                >
                  {scoreDelta > 0 ? '+' : ''}
                  {scoreDelta}
                </div>
              )}
              <div style={{ fontSize: 11, color: '#6b6b8a', marginTop: 4 }}>SCORE</div>
            </div>

            {/* Severity summary */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {Object.entries(SEVERITY_CONFIG).map(([key, cfg]) => {
                const count = reviewData.severity_counts[key] || 0;
                if (count === 0) return null;
                return (
                  <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: cfg.color,
                      }}
                    />
                    <Text style={{ color: '#b8c9dc', fontSize: 12 }}>
                      {count} {cfg.label.toLowerCase()}
                    </Text>
                  </div>
                );
              })}
              {reviewData.findings.length === 0 && (
                <Text style={{ color: '#52c41a', fontSize: 12 }}>No issues found</Text>
              )}
            </div>
          </div>

          {/* AI Summary */}
          <div
            style={{
              background: '#1e2a3a',
              borderRadius: 8,
              padding: '12px 16px',
              borderLeft: '3px solid #1890ff',
              marginBottom: 16,
            }}
          >
            <Text style={{ color: '#b8c9dc', fontSize: 13, lineHeight: 1.6 }}>
              {reviewData.summary}
            </Text>
          </div>

          {/* Findings by category */}
          {collapseItems.length > 0 ? (
            <Collapse
              defaultActiveKey={collapseItems
                .filter((item) =>
                  findingsByCategory[item.key]?.some(
                    (e) => e.finding.severity === 'critical' || e.finding.severity === 'warning'
                  )
                )
                .map((item) => item.key)}
              ghost
              items={collapseItems}
              style={{
                background: 'transparent',
              }}
            />
          ) : (
            <Empty
              image={<CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />}
              description={
                <Text style={{ color: '#6b6b8a' }}>Scenario looks good! No issues found.</Text>
              }
              style={{ marginTop: 40 }}
            />
          )}
        </>
      )}

      {/* Initial empty state (no data, no loading, no error) */}
      {!reviewData && !loading && !error && (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Title level={5} style={{ color: '#6b6b8a' }}>
            Click Re-run to analyze this scenario
          </Title>
        </div>
      )}
    </Drawer>
  );
};

export default ScenarioReviewDrawer;
