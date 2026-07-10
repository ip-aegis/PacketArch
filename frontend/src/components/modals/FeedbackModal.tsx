/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React, { useState } from 'react';
import { Modal, Form, Input, Alert, message } from 'antd';
import { MessageOutlined } from '@ant-design/icons';
import { feedbackApi } from '../../api/feedback';
import { extractErrorMessage } from '../../utils/errorUtils';

interface FeedbackModalProps {
  open: boolean;
  onClose: () => void;
}

interface FormValues {
  name: string;
  email: string;
  message: string;
}

const FeedbackModal: React.FC<FeedbackModalProps> = ({ open, onClose }) => {
  const [form] = Form.useForm<FormValues>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (values: FormValues) => {
    setError(null);
    setLoading(true);
    try {
      await feedbackApi.submit(values);
      message.success('Feedback sent — thank you!');
      form.resetFields();
      onClose();
    } catch (err) {
      setError(extractErrorMessage(err) || 'Failed to send feedback');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    setError(null);
    onClose();
  };

  return (
    <Modal
      title={
        <span>
          <MessageOutlined style={{ marginRight: 8 }} />
          Send Feedback
        </span>
      }
      open={open}
      onOk={() => form.submit()}
      onCancel={handleCancel}
      okText="Send"
      okButtonProps={{ loading }}
      destroyOnClose
    >
      <p style={{ color: '#a8a8c0', marginBottom: 16, marginTop: 4 }}>
        Your message will be sent directly to the PacketArch team.
      </p>

      {error && (
        <Alert
          message={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item
          name="name"
          label="Name"
          rules={[{ required: true, message: 'Please enter your name' }]}
        >
          <Input placeholder="Your name" maxLength={100} />
        </Form.Item>

        <Form.Item
          name="email"
          label="Email"
          rules={[
            { required: true, message: 'Please enter your email' },
            { type: 'email', message: 'Enter a valid email address' },
          ]}
        >
          <Input placeholder="your@email.com" maxLength={200} />
        </Form.Item>

        <Form.Item
          name="message"
          label="Message"
          rules={[{ required: true, message: 'Please enter a message' }]}
        >
          <Input.TextArea
            placeholder="Bug report, feature request, or general feedback..."
            rows={5}
            maxLength={2000}
            showCount
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default FeedbackModal;
