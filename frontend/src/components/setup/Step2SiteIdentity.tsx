/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React from 'react';
import { Form, Input, Select, Typography } from 'antd';
import type { FormInstance } from 'antd';
import type { SiteIdentityInput } from '../../api/setup';

const { Text } = Typography;

// A small curated list of common time zones. Operators with exotic zones can
// type a custom IANA name (the field accepts free input via mode="combobox").
const COMMON_TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Singapore',
  'Asia/Dubai',
  'Australia/Sydney',
];

interface Props {
  form: FormInstance<SiteIdentityInput>;
  initial?: Partial<SiteIdentityInput>;
}

const Step2SiteIdentity: React.FC<Props> = ({ form, initial }) => (
  <Form form={form} layout="vertical" initialValues={initial} requiredMark>
    <Text type="secondary">
      How this PacketArch installation identifies itself. The FQDN is baked
      into agent install commands — get it right.
    </Text>
    <Form.Item
      name="name"
      label="Site name"
      style={{ marginTop: 16 }}
      tooltip="Shown in the title bar and briefing decks. Examples: 'OT Lab Bench A', 'Acme Manufacturing Pilot'."
      rules={[{ required: true, message: 'Site name is required' }]}
    >
      <Input autoFocus placeholder="My OT Lab" />
    </Form.Item>

    <Form.Item
      name="fqdn"
      label="Server FQDN or IP"
      tooltip="Used in agent install commands. Pick the address agents will reach this server at."
      rules={[
        { required: true, message: 'FQDN or IP is required' },
        {
          pattern: /^[a-zA-Z0-9._-]+$/,
          message: 'Hostname / FQDN format only (no protocol, no path)',
        },
      ]}
    >
      <Input placeholder="packetarch.lab.local" />
    </Form.Item>

    <Form.Item
      name="timezone"
      label="Site time zone"
      tooltip="The server's time zone — used for timestamps in scenarios and logs. Pick where the SERVER lives, not where you (the operator) live."
      rules={[{ required: true, message: 'Time zone is required' }]}
    >
      <Select
        showSearch
        placeholder="Select or type an IANA time zone"
        options={COMMON_TIMEZONES.map((tz) => ({ value: tz, label: tz }))}
        filterOption={(input, option) =>
          (option?.label as string).toLowerCase().includes(input.toLowerCase())
        }
      />
    </Form.Item>
  </Form>
);

export default Step2SiteIdentity;
