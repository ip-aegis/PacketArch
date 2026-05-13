/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Compact badge row for scenario-level mode flags.
 *
 * Drop into list/detail surfaces (scenario cards, deployment cards, live
 * traffic rows, studio info pane) to communicate at a glance which
 * non-default modes a scenario is running with. Stays empty when nothing
 * interesting is set so it never adds visual noise to default scenarios.
 *
 * To add a new mode badge: extend `Modes` here, render a new <Tag/>, and
 * add the corresponding flag to ScenarioModes in api/scenarios.ts.
 */

import React from 'react';
import { Tag, Tooltip } from 'antd';
import {
  ExperimentOutlined,
  WifiOutlined,
  LockOutlined,
} from '@ant-design/icons';

export interface Modes {
  cleanDemoMode?: boolean;
  broadcastTrafficEnabled?: boolean;
  cellIsolationMode?: string;
}

interface Props {
  modes: Modes;
  size?: 'small' | 'default';
  /** Show all badges including defaults. Off by default — only non-default
   *  modes render so the row is empty when nothing's interesting. */
  showAll?: boolean;
}

const ScenarioModeBadges: React.FC<Props> = ({
  modes,
  size = 'small',
  showAll = false,
}) => {
  const badges: React.ReactNode[] = [];

  if (modes.cleanDemoMode || showAll) {
    const on = modes.cleanDemoMode === true;
    badges.push(
      <Tooltip
        key="clean-demo"
        title={
          on
            ? 'Clean Demo Mode: cyclic traffic suppressed (PROFINET PN-IO). Optimised for asset-classification DPI tools like Cyber Vision.'
            : 'Clean Demo Mode is off — full protocol traffic.'
        }
      >
        <Tag
          icon={<ExperimentOutlined />}
          color={on ? 'gold' : 'default'}
          style={size === 'small' ? { fontSize: 11, padding: '0 6px' } : undefined}
        >
          {on ? 'Clean Demo' : 'Full Traffic'}
        </Tag>
      </Tooltip>
    );
  }

  if (modes.broadcastTrafficEnabled === false || showAll) {
    const off = modes.broadcastTrafficEnabled === false;
    badges.push(
      <Tooltip
        key="broadcast"
        title={
          off
            ? 'Broadcast/multicast traffic disabled: ARP, NTP, LLDP, STP, CDP, DHCP, IGMP, BACnet Who-Is, PROFINET DCP, SNMP traps not generated.'
            : 'Broadcast/multicast traffic enabled.'
        }
      >
        <Tag
          icon={<WifiOutlined />}
          color={off ? 'red' : 'cyan'}
          style={size === 'small' ? { fontSize: 11, padding: '0 6px' } : undefined}
        >
          {off ? 'No Broadcast' : 'Broadcast'}
        </Tag>
      </Tooltip>
    );
  }

  if (
    (modes.cellIsolationMode && modes.cellIsolationMode !== 'off') ||
    showAll
  ) {
    const mode = modes.cellIsolationMode ?? 'off';
    const label =
      mode === 'strict_northbound'
        ? 'Strict Cells'
        : mode === 'conduit_gated'
          ? 'Conduit-Gated'
          : 'Cells Open';
    const color = mode === 'strict_northbound'
      ? 'volcano'
      : mode === 'conduit_gated' ? 'orange' : 'default';
    badges.push(
      <Tooltip
        key="cell-isolation"
        title={
          mode === 'strict_northbound'
            ? 'Strict cell isolation: cell↔cell traffic blocked at runtime; cells may only talk to L3+ zones.'
            : mode === 'conduit_gated'
              ? 'Conduit-gated isolation: cell↔cell traffic dropped unless an explicit conduit permits the protocol.'
              : 'Cell isolation off: cross-cell traffic is allowed.'
        }
      >
        <Tag
          icon={<LockOutlined />}
          color={color}
          style={size === 'small' ? { fontSize: 11, padding: '0 6px' } : undefined}
        >
          {label}
        </Tag>
      </Tooltip>
    );
  }

  if (badges.length === 0) return null;

  return (
    <span
      style={{
        display: 'inline-flex',
        gap: 4,
        flexWrap: 'wrap',
        alignItems: 'center',
      }}
    >
      {badges}
    </span>
  );
};

/** Convenience: build a Modes object from a backend ScenarioSummary.modes. */
export function modesFromSummary(
  summary: { modes?: { clean_demo_mode?: boolean; broadcast_traffic_enabled?: boolean; cell_isolation_mode?: string } } | null | undefined,
): Modes {
  if (!summary?.modes) return {};
  return {
    cleanDemoMode: summary.modes.clean_demo_mode,
    broadcastTrafficEnabled: summary.modes.broadcast_traffic_enabled,
    cellIsolationMode: summary.modes.cell_isolation_mode,
  };
}

/** Convenience: build a Modes object from a raw scenario.definition object. */
export function modesFromDefinition(
  definition: Record<string, unknown> | null | undefined,
): Modes {
  if (!definition) return {};
  const ci = definition.cell_isolation as { mode?: string } | undefined;
  return {
    cleanDemoMode: definition.clean_demo_mode === true,
    broadcastTrafficEnabled: definition.broadcast_traffic_enabled !== false,
    cellIsolationMode: ci?.mode ?? 'off',
  };
}

export default ScenarioModeBadges;
