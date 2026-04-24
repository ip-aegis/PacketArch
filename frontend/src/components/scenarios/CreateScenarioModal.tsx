/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * CreateScenarioModal - Modal dialog for creating a new blank scenario.
 */

import React from 'react';
import { Modal, Form, Input, Select, Space, Button, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import type { ScenarioCreate } from '../../api/scenarios';
import { verticalConfig } from './scenarioConstants';

const { Text } = Typography;
const { Option } = Select;

export interface CreateScenarioModalProps {
  open: boolean;
  loading: boolean;
  onCancel: () => void;
  onSubmit: (values: ScenarioCreate) => void;
}

const CreateScenarioModal: React.FC<CreateScenarioModalProps> = ({
  open,
  loading,
  onCancel,
  onSubmit,
}) => {
  const [form] = Form.useForm();

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  const handleFinish = (values: ScenarioCreate) => {
    onSubmit({
      ...values,
      definition: {
        devices: {},
        flows: {},
        zones: {},
        phases: [],
      },
    });
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background:
                'linear-gradient(135deg, #049FD920 0%, #049FD910 100%)',
              border: '1px solid #049FD940',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#049FD9',
            }}
          >
            <PlusOutlined style={{ fontSize: 18 }} />
          </div>
          <span style={{ color: '#fff', fontSize: 16 }}>
            Create New Scenario
          </span>
        </div>
      }
      open={open}
      onCancel={handleCancel}
      footer={null}
      styles={{
        header: {
          background: '#141428',
          borderBottom: '1px solid #2d2d52',
        },
        body: { background: '#1a1a2e', padding: 24 },
        content: { background: '#141428' },
      }}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={{ total_duration_ms: 60000 }}
      >
        <Form.Item
          name="name"
          label={<Text style={{ color: '#a8a8c0' }}>Scenario Name</Text>}
          rules={[
            { required: true, message: 'Please enter a scenario name' },
          ]}
        >
          <Input placeholder="My OT Scenario" />
        </Form.Item>

        <Form.Item
          name="description"
          label={<Text style={{ color: '#a8a8c0' }}>Description</Text>}
        >
          <Input.TextArea rows={3} placeholder="Describe your scenario..." />
        </Form.Item>

        <Form.Item
          name="vertical"
          label={
            <Text style={{ color: '#a8a8c0' }}>Industry Vertical</Text>
          }
        >
          <Select placeholder="Select a vertical (optional)" allowClear>
            {Object.entries(verticalConfig).map(([key, config]) => (
              <Option key={key} value={key}>
                <Space>
                  {config.icon}
                  {config.label}
                </Space>
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="total_duration_ms"
          label={<Text style={{ color: '#a8a8c0' }}>Duration (ms)</Text>}
        >
          <Select>
            <Option value={10000}>10 seconds</Option>
            <Option value={30000}>30 seconds</Option>
            <Option value={60000}>1 minute</Option>
            <Option value={300000}>5 minutes</Option>
            <Option value={600000}>10 minutes</Option>
            <Option value={1800000}>30 minutes</Option>
            <Option value={3600000}>1 hour</Option>
          </Select>
        </Form.Item>

        <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={handleCancel}>Cancel</Button>
            <Button type="primary" htmlType="submit" loading={loading}>
              Create Scenario
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default CreateScenarioModal;
