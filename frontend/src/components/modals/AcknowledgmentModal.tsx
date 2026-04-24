/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * First-run acknowledgment modal.
 *
 * Shown after login when the current user has not yet accepted the current
 * acknowledgment document version. Blocking — no close, no escape, only the
 * "I acknowledge" path proceeds. If the user declines, they are logged out.
 */

import React, { useEffect, useState } from 'react';
import { Modal, Checkbox, Typography, Space, Button, Alert } from 'antd';
import { aboutApi, type AcknowledgmentInfo } from '../../api/about';
import { acknowledgmentsApi } from '../../api/acknowledgments';
import { useAuthStore } from '../../stores/authStore';

const { Paragraph, Text } = Typography;

interface AcknowledgmentModalProps {
  open: boolean;
  onAccepted: () => void;
}

const AcknowledgmentModal: React.FC<AcknowledgmentModalProps> = ({
  open,
  onAccepted,
}) => {
  const [ack, setAck] = useState<AcknowledgmentInfo | null>(null);
  const [checked, setChecked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const logout = useAuthStore((s) => s.logout);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    aboutApi
      .get()
      .then((data) => {
        if (!cancelled) setAck(data.acknowledgment);
      })
      .catch(() => {
        if (!cancelled) setError('Could not load acknowledgment text.');
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const handleAccept = async () => {
    if (!ack) return;
    setSubmitting(true);
    setError(null);
    try {
      await acknowledgmentsApi.accept({
        document: ack.document,
        version: ack.version,
      });
      onAccepted();
    } catch {
      setError('Could not record acknowledgment. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDecline = () => {
    logout();
    window.location.href = '/login';
  };

  return (
    <Modal
      title={ack?.title || 'Welcome'}
      open={open}
      closable={false}
      maskClosable={false}
      keyboard={false}
      footer={null}
      width={560}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {error && <Alert type="error" message={error} showIcon />}

        {ack && (
          <>
            {ack.body.split('\n\n').map((para, i) => (
              <Paragraph key={i} style={{ margin: 0 }}>
                {para}
              </Paragraph>
            ))}

            <Text type="secondary" style={{ fontSize: 12 }}>
              Document: {ack.document} · version {ack.version}
            </Text>

            <Checkbox
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
            >
              I acknowledge
            </Checkbox>

            <Space style={{ justifyContent: 'flex-end', width: '100%' }}>
              <Button onClick={handleDecline} disabled={submitting}>
                Decline &amp; sign out
              </Button>
              <Button
                type="primary"
                disabled={!checked || submitting}
                loading={submitting}
                onClick={handleAccept}
              >
                Continue
              </Button>
            </Space>
          </>
        )}
      </Space>
    </Modal>
  );
};

export default AcknowledgmentModal;
