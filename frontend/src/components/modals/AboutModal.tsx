/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * About modal — product name, version, build info, ownership, license.
 * Opened from the user dropdown in the header.
 */

import React, { useEffect, useState } from 'react';
import { Modal, Typography, Space, Divider, Skeleton, Alert } from 'antd';
import { aboutApi, type AboutResponse } from '../../api/about';

const { Text, Title, Link } = Typography;

interface AboutModalProps {
  open: boolean;
  onClose: () => void;
}

const AboutModal: React.FC<AboutModalProps> = ({ open, onClose }) => {
  const [info, setInfo] = useState<AboutResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    aboutApi
      .get()
      .then((data) => {
        if (!cancelled) setInfo(data);
      })
      .catch(() => {
        if (!cancelled) setError('Could not load product information.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  return (
    <Modal
      title="About PacketArch"
      open={open}
      onCancel={onClose}
      onOk={onClose}
      okText="Close"
      cancelButtonProps={{ style: { display: 'none' } }}
      width={560}
    >
      {loading && <Skeleton active paragraph={{ rows: 6 }} />}
      {error && <Alert type="error" message={error} showIcon />}
      {info && (
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Title level={4} style={{ margin: 0 }}>
              {info.name} v{info.version}
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Build {info.build_commit} · {info.build_date.split('T')[0]}
            </Text>
          </div>

          <Divider style={{ margin: '8px 0' }} />

          <div>
            <Text strong>Developed and maintained by</Text>
            <br />
            <Text>{info.owner.name}</Text>
            <br />
            <Link href={`mailto:${info.owner.email}`}>{info.owner.email}</Link>
          </div>

          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {info.owner.copyright}. All rights reserved.
            </Text>
          </div>

          <Divider style={{ margin: '8px 0' }} />

          <div>
            <Text strong>License</Text>
            <br />
            <Text>
              {info.license.name} ({info.license.id})
            </Text>
            <br />
            <Link href={info.license.url} target="_blank" rel="noopener noreferrer">
              {info.license.url}
            </Link>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              Redistribution — modified or unmodified — must preserve copyright
              notices and license text as required by GPL-3.0.
            </Text>
          </div>

          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Third-party components are distributed under their own respective
              licenses. See THIRD_PARTY_LICENSES.md for attributions.
            </Text>
          </div>
        </Space>
      )}
    </Modal>
  );
};

export default AboutModal;
