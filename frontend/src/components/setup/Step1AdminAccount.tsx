/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React from 'react';
import { Form, Input, Typography } from 'antd';
import type { FormInstance } from 'antd';
import type { AdminAccountInput } from '../../api/setup';

const { Text } = Typography;

interface Props {
  form: FormInstance<AdminAccountInput & { password_confirm: string }>;
  initial?: Partial<AdminAccountInput>;
}

const Step1AdminAccount: React.FC<Props> = ({ form, initial }) => (
  <Form form={form} layout="vertical" initialValues={initial} requiredMark>
    <Text type="secondary">
      The first admin account. You'll use these credentials to log in after
      setup completes.
    </Text>
    <Form.Item
      name="username"
      label="Admin username"
      style={{ marginTop: 16 }}
      rules={[
        { required: true, message: 'Username is required' },
        { min: 3, max: 64, message: 'Between 3 and 64 characters' },
        {
          pattern: /^[a-zA-Z0-9_.-]+$/,
          message: 'Letters, numbers, dot, underscore, hyphen only',
        },
      ]}
    >
      <Input autoComplete="username" autoFocus />
    </Form.Item>

    <Form.Item
      name="password"
      label="Password"
      rules={[
        { required: true, message: 'Password is required' },
        { min: 8, message: 'At least 8 characters' },
      ]}
      hasFeedback
    >
      <Input.Password autoComplete="new-password" />
    </Form.Item>

    <Form.Item
      name="password_confirm"
      label="Confirm password"
      dependencies={['password']}
      hasFeedback
      rules={[
        { required: true, message: 'Confirm your password' },
        ({ getFieldValue }) => ({
          validator(_, value) {
            if (!value || getFieldValue('password') === value) {
              return Promise.resolve();
            }
            return Promise.reject(new Error("Passwords don't match"));
          },
        }),
      ]}
    >
      <Input.Password autoComplete="new-password" />
    </Form.Item>

    <Form.Item
      name="email"
      label="Email (optional)"
      rules={[{ type: 'email', message: 'Enter a valid email or leave blank' }]}
    >
      <Input autoComplete="email" placeholder="admin@example.com" />
    </Form.Item>
  </Form>
);

export default Step1AdminAccount;
