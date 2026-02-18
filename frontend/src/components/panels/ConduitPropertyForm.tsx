/**
 * Conduit property form for right sidebar.
 * Edit conduit name, direction, allowed protocols, security level.
 */

import React from 'react';
import { Form, Input, Select, Tag, Typography, Divider, Empty } from 'antd';
import { useScenarioStore } from '../../stores/scenarioStore';
import type { ConduitDirection, ProtocolType } from '../../types';
import { PROTOCOL_OPTIONS, getProtocolLabel, getProtocolColor } from '../../constants/protocols';
import { TEXT_BODY, TEXT_MUTED, BG_CODE, BORDER_DEFAULT } from '../../constants/theme';

const { Text } = Typography;
const { TextArea } = Input;

const DIRECTION_OPTIONS: { value: ConduitDirection; label: string }[] = [
  { value: 'bidirectional', label: '\u2194 Bidirectional' },
  { value: 'a_to_b', label: '\u2192 Source \u2192 Target' },
  { value: 'b_to_a', label: '\u2190 Target \u2192 Source' },
];

const SECURITY_LEVEL_OPTIONS = [
  { value: 'minimal', label: 'SL 0 \u2014 Minimal' },
  { value: 'standard', label: 'SL 1 \u2014 Standard' },
  { value: 'high', label: 'SL 2 \u2014 High' },
  { value: 'critical', label: 'SL 3 \u2014 Critical' },
];

const SECURITY_LEVEL_COLORS: Record<string, string> = {
  minimal: '#8c8c8c',
  standard: '#1890ff',
  high: '#faad14',
  critical: '#ff4d4f',
};

// Extended protocol options including variant protocols used in templates
const ALL_PROTOCOL_OPTIONS: { value: string; label: string }[] = [
  ...PROTOCOL_OPTIONS,
  { value: 'profisafe', label: 'PROFIsafe' },
  { value: 'cip_safety', label: 'CIP Safety' },
  { value: 's7comm_plus', label: 'S7comm+' },
  { value: 'snmp', label: 'SNMP' },
  { value: 'https', label: 'HTTPS' },
  { value: 'rdp', label: 'RDP' },
];

interface ConduitPropertyFormProps {
  conduitId: string;
}

const ConduitPropertyForm: React.FC<ConduitPropertyFormProps> = ({ conduitId }) => {
  const conduit = useScenarioStore((state) => state.conduits[conduitId]);
  const zones = useScenarioStore((state) => state.zones);
  const updateConduit = useScenarioStore((state) => state.updateConduit);

  if (!conduit) {
    return <Empty description="Conduit not found" />;
  }

  const sourceZone = zones[conduit.sourceZoneId];
  const targetZone = zones[conduit.targetZoneId];
  const securityColor = SECURITY_LEVEL_COLORS[conduit.securityLevel || 'standard'];

  return (
    <div style={{ padding: '0 4px' }}>
      <Text strong style={{ color: TEXT_BODY, display: 'block', marginBottom: 16 }}>
        Conduit Properties
      </Text>

      {/* Name */}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 4 }}>
          Name
        </Text>
        <Input
          value={conduit.name}
          onChange={(e) => updateConduit(conduitId, { name: e.target.value })}
          style={{ background: BG_CODE, border: `1px solid ${BORDER_DEFAULT}`, color: TEXT_BODY }}
        />
      </div>

      {/* Connected Zones */}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 4 }}>
          Connected Zones
        </Text>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: BG_CODE, border: `1px solid ${BORDER_DEFAULT}`,
          borderRadius: 6, padding: '8px 12px',
        }}>
          <Tag color="blue" style={{ margin: 0 }}>
            {sourceZone?.name || conduit.sourceZoneId}
            {sourceZone?.level != null && (
              <span style={{ fontSize: 10, opacity: 0.7 }}> L{sourceZone.level}</span>
            )}
          </Tag>
          <span style={{ color: TEXT_MUTED, fontSize: 16 }}>
            {conduit.direction === 'a_to_b' ? '\u2192' : conduit.direction === 'b_to_a' ? '\u2190' : '\u2194'}
          </span>
          <Tag color="blue" style={{ margin: 0 }}>
            {targetZone?.name || conduit.targetZoneId}
            {targetZone?.level != null && (
              <span style={{ fontSize: 10, opacity: 0.7 }}> L{targetZone.level}</span>
            )}
          </Tag>
        </div>
      </div>

      {/* Direction */}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 4 }}>
          Direction
        </Text>
        <Select
          value={conduit.direction}
          onChange={(value: ConduitDirection) => updateConduit(conduitId, { direction: value })}
          options={DIRECTION_OPTIONS}
          style={{ width: '100%' }}
          popupMatchSelectWidth={false}
        />
      </div>

      <Divider style={{ borderColor: BORDER_DEFAULT, margin: '16px 0' }} />

      {/* Allowed Protocols */}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 4 }}>
          Allowed Protocols
        </Text>
        <Select
          mode="multiple"
          value={conduit.allowedProtocols}
          onChange={(value: ProtocolType[]) => updateConduit(conduitId, { allowedProtocols: value })}
          options={ALL_PROTOCOL_OPTIONS}
          style={{ width: '100%' }}
          placeholder="Select allowed protocols..."
          tagRender={(props) => {
            const { label, value, closable, onClose } = props;
            const color = getProtocolColor(value as string);
            return (
              <Tag
                color={color}
                closable={closable}
                onClose={onClose}
                style={{ marginRight: 4, marginBottom: 2 }}
              >
                {label}
              </Tag>
            );
          }}
        />
      </div>

      {/* Security Level */}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 4 }}>
          Security Level (IEC 62443)
        </Text>
        <Select
          value={conduit.securityLevel || 'standard'}
          onChange={(value) => updateConduit(conduitId, { securityLevel: value })}
          options={SECURITY_LEVEL_OPTIONS}
          style={{ width: '100%' }}
        />
        <div style={{ marginTop: 4 }}>
          <span style={{
            display: 'inline-block', width: 8, height: 8,
            borderRadius: '50%', background: securityColor, marginRight: 6,
          }} />
          <Text style={{ fontSize: 11, color: TEXT_MUTED }}>
            {conduit.securityLevel === 'critical' ? 'Maximum restrictions, life-safety systems' :
             conduit.securityLevel === 'high' ? 'Strict access control, industrial control' :
             conduit.securityLevel === 'minimal' ? 'Minimal restrictions, monitoring only' :
             'Standard access control, general operations'}
          </Text>
        </div>
      </div>

      <Divider style={{ borderColor: BORDER_DEFAULT, margin: '16px 0' }} />

      {/* Description */}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 4 }}>
          Description
        </Text>
        <TextArea
          rows={2}
          value={conduit.description || ''}
          onChange={(e) => updateConduit(conduitId, { description: e.target.value })}
          placeholder="Describe this conduit's purpose..."
          style={{
            background: BG_CODE,
            border: `1px solid ${BORDER_DEFAULT}`,
            color: TEXT_BODY,
            resize: 'vertical',
          }}
        />
      </div>

      {/* Auto-generated badge */}
      {conduit.autoGenerated && (
        <div style={{ marginTop: 8 }}>
          <Tag color="default" style={{ fontSize: 10 }}>Auto-generated from Purdue adjacency</Tag>
        </div>
      )}
    </div>
  );
};

export default ConduitPropertyForm;
