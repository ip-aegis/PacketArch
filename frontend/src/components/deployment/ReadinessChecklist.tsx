/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * ReadinessChecklist - Shows scenario readiness checks in the deployment panel.
 */

import React, { useCallback, useEffect, useState } from 'react';
import {
  Button,
  Progress,
  Space,
  Tooltip,
  Typography,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import {
  scenariosApi,
  type ScenarioValidationResponse,
} from '../../api/scenarios';
import { extractErrorMessage } from '../../utils/errorUtils';

const { Text } = Typography;

interface ReadinessChecklistProps {
  scenarioId: string;
  onReadinessChange?: (hasErrors: boolean) => void;
}

interface AggregatedCheck {
  name: string;
  passed: boolean;
  severity: 'error' | 'warning';
  message: string | null;
  code: string;
}

function aggregateValidation(
  validation: ScenarioValidationResponse,
): AggregatedCheck[] {
  const checks: AggregatedCheck[] = [];

  const hasDevices = validation.device_count > 0;
  checks.push({
    name: 'Has devices',
    passed: hasDevices,
    severity: 'error',
    message: hasDevices ? null : 'Scenario has no devices',
    code: 'no_devices',
  });

  const hasFlows = validation.flow_count > 0;
  checks.push({
    name: 'Has flows',
    passed: hasFlows,
    severity: 'error',
    message: hasFlows ? null : 'Scenario has no flows',
    code: 'no_flows',
  });

  const incompleteFlows = validation.warnings.filter(
    (w) => w.code === 'incomplete_flow',
  );
  checks.push({
    name: 'All flows have endpoints',
    passed: incompleteFlows.length === 0,
    severity: 'error',
    message:
      incompleteFlows.length > 0
        ? `${incompleteFlows.length} flow(s) missing endpoints`
        : null,
    code: 'incomplete_flow',
  });

  const dupNames = validation.warnings.filter(
    (w) => w.code === 'duplicate_device_name',
  );
  checks.push({
    name: 'Unique device names',
    passed: dupNames.length === 0,
    severity: 'error',
    message:
      dupNames.length > 0
        ? `${dupNames.length} duplicate name(s)`
        : null,
    code: 'duplicate_device_name',
  });

  const dupMacs = validation.warnings.filter(
    (w) => w.code === 'duplicate_mac_address',
  );
  checks.push({
    name: 'Unique MAC addresses',
    passed: dupMacs.length === 0,
    severity: 'error',
    message:
      dupMacs.length > 0 ? `${dupMacs.length} duplicate MAC(s)` : null,
    code: 'duplicate_mac_address',
  });

  const missingIps = validation.warnings.filter(
    (w) => w.code === 'missing_ip',
  );
  checks.push({
    name: 'All devices have IPs',
    passed: missingIps.length === 0,
    severity: 'warning',
    message:
      missingIps.length > 0
        ? `${missingIps.length} device(s) missing IP`
        : null,
    code: 'missing_ip',
  });

  const orphans = validation.warnings.filter(
    (w) => w.code === 'orphan_device',
  );
  checks.push({
    name: 'No orphan devices',
    passed: orphans.length === 0,
    severity: 'warning',
    message:
      orphans.length > 0
        ? `${orphans.length} device(s) with no flows`
        : null,
    code: 'orphan_device',
  });

  const protocolIssues = validation.warnings.filter(
    (w) => w.code === 'protocol_identity_mismatch',
  );
  checks.push({
    name: 'Protocol/fingerprint consistency',
    passed: protocolIssues.length === 0,
    severity: 'warning',
    message:
      protocolIssues.length > 0
        ? `${protocolIssues.length} protocol mismatch(es)`
        : null,
    code: 'protocol_identity_mismatch',
  });

  return checks;
}

const ReadinessChecklist: React.FC<ReadinessChecklistProps> = ({
  scenarioId,
  onReadinessChange,
}) => {
  const [loading, setLoading] = useState(false);
  const [repairing, setRepairing] = useState(false);
  const [checks, setChecks] = useState<AggregatedCheck[]>([]);
  const [hasProtocolMismatch, setHasProtocolMismatch] = useState(false);

  const validate = useCallback(async () => {
    setLoading(true);
    try {
      const result = await scenariosApi.validate(scenarioId);
      const aggregated = aggregateValidation(result);
      setChecks(aggregated);
      setHasProtocolMismatch(
        result.warnings.some(
          (w) => w.code === 'protocol_identity_mismatch',
        ),
      );
      const hasErrors = aggregated.some(
        (c) => !c.passed && c.severity === 'error',
      );
      onReadinessChange?.(hasErrors);
    } catch (err) {
      message.error(
        extractErrorMessage(err, 'Failed to validate scenario'),
      );
    } finally {
      setLoading(false);
    }
  }, [scenarioId, onReadinessChange]);

  useEffect(() => {
    validate();
  }, [validate]);

  const handleRepair = async () => {
    setRepairing(true);
    try {
      const result = await scenariosApi.repairProtocols(scenarioId);
      message.success(result.message);
      await validate();
    } catch (err) {
      message.error(
        extractErrorMessage(err, 'Failed to repair protocols'),
      );
    } finally {
      setRepairing(false);
    }
  };

  const total = checks.length;
  const passed = checks.filter((c) => c.passed).length;
  const score = total > 0 ? Math.round((passed / total) * 100) : 0;
  const errorCount = checks.filter(
    (c) => !c.passed && c.severity === 'error',
  ).length;
  const warningCount = checks.filter(
    (c) => !c.passed && c.severity === 'warning',
  ).length;

  const progressColor =
    errorCount > 0
      ? '#ff4d4f'
      : warningCount > 0
        ? '#faad14'
        : '#52c41a';

  return (
    <div
      style={{
        background: '#1a2734',
        border: '1px solid #2a3f54',
        borderRadius: 8,
        padding: 12,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 8,
        }}
      >
        <Text
          strong
          style={{ color: '#8aa4bc', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px' }}
        >
          Readiness
        </Text>
        <Space size={4}>
          {hasProtocolMismatch && (
            <Tooltip title="Fix protocol/fingerprint mismatches">
              <Button
                type="text"
                size="small"
                icon={<ToolOutlined />}
                onClick={handleRepair}
                loading={repairing}
                style={{ color: '#faad14', fontSize: 11 }}
              >
                Repair
              </Button>
            </Tooltip>
          )}
          <Tooltip title="Re-validate">
            <Button
              type="text"
              size="small"
              icon={<ReloadOutlined />}
              onClick={validate}
              loading={loading}
              style={{ color: '#6a8caf' }}
            />
          </Tooltip>
        </Space>
      </div>

      {/* Progress */}
      <Progress
        percent={score}
        size="small"
        strokeColor={progressColor}
        format={(pct) => (
          <span style={{ color: progressColor, fontSize: 12 }}>
            {pct}%
          </span>
        )}
        style={{ marginBottom: 8 }}
      />

      {/* Checks list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {checks.map((check) => (
          <div
            key={check.code}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '2px 0',
            }}
          >
            {check.passed ? (
              <CheckCircleOutlined
                style={{ color: '#52c41a', fontSize: 12 }}
              />
            ) : check.severity === 'error' ? (
              <CloseCircleOutlined
                style={{ color: '#ff4d4f', fontSize: 12 }}
              />
            ) : (
              <ExclamationCircleOutlined
                style={{ color: '#faad14', fontSize: 12 }}
              />
            )}
            <Text
              style={{
                color: check.passed ? '#6a8caf' : '#e6f1ff',
                fontSize: 12,
                flex: 1,
              }}
            >
              {check.name}
            </Text>
            {check.message && (
              <Text
                style={{
                  color:
                    check.severity === 'error'
                      ? '#ff4d4f'
                      : '#faad14',
                  fontSize: 10,
                }}
              >
                {check.message}
              </Text>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ReadinessChecklist;
