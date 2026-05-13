/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React, { useEffect, useState } from 'react';
import { Card, Checkbox, Space, Typography, Descriptions } from 'antd';
import { aboutApi } from '../../api/about';
import type {
  AdminAccountInput,
  SiteIdentityInput,
} from '../../api/setup';
import type { Step3Values } from './Step3Capabilities';

const { Text } = Typography;

interface Props {
  admin: AdminAccountInput;
  site: SiteIdentityInput;
  capabilities: Step3Values;
  acknowledgmentAccepted: boolean;
  onAcknowledgmentChange: (accepted: boolean) => void;
}

const Step4Confirm: React.FC<Props> = ({
  admin,
  site,
  capabilities,
  acknowledgmentAccepted,
  onAcknowledgmentChange,
}) => {
  const [ackBody, setAckBody] = useState<string>('');
  const [ackTitle, setAckTitle] = useState<string>('Welcome to PacketArch');
  const [licenseId, setLicenseId] = useState<string>('GPL-3.0');

  // Load the GPL acknowledgment text from /about so we don't duplicate it.
  useEffect(() => {
    aboutApi
      .get()
      .then((about) => {
        setAckBody(about.acknowledgment.body);
        setAckTitle(about.acknowledgment.title);
        setLicenseId(about.license.id);
      })
      .catch(() => {
        setAckBody(
          'PacketArch is licensed under GPL-3.0. By continuing you accept the terms in the LICENSE file shipped with this installation.',
        );
      });
  }, []);

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Text type="secondary">
        Review your settings, accept the {licenseId} acknowledgment, and click
        <b> Complete setup</b>.
      </Text>

      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="Admin username">
          {admin.username}
        </Descriptions.Item>
        <Descriptions.Item label="Admin email">
          {admin.email || <Text type="secondary">(none)</Text>}
        </Descriptions.Item>
        <Descriptions.Item label="Site name">{site.name}</Descriptions.Item>
        <Descriptions.Item label="Server FQDN / IP">
          {site.fqdn}
        </Descriptions.Item>
        <Descriptions.Item label="Time zone">{site.timezone}</Descriptions.Item>
        <Descriptions.Item label="AI features">
          {capabilities.ai_enabled
            ? capabilities.ai_anthropic_api_key
              ? 'Enabled (key provided)'
              : 'Enabled (add key in Settings later)'
            : 'Disabled'}
        </Descriptions.Item>
        <Descriptions.Item label="Cyber Vision">
          {capabilities.cv_enabled ? capabilities.cv_url || '(URL not set)' : 'Disabled'}
        </Descriptions.Item>
      </Descriptions>

      <Card title={ackTitle} size="small">
        <Text style={{ whiteSpace: 'pre-line' }}>{ackBody}</Text>
        <div style={{ marginTop: 16 }}>
          <Checkbox
            checked={acknowledgmentAccepted}
            onChange={(e) => onAcknowledgmentChange(e.target.checked)}
          >
            I acknowledge and accept these terms.
          </Checkbox>
        </div>
      </Card>
    </Space>
  );
};

export default Step4Confirm;
