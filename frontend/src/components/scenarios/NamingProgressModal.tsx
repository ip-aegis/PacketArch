/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * NamingProgressModal — blocking provisioning screen shown after a
 * scenario is created from a template while its AI device-naming runs in
 * the background. Studio only opens once naming succeeds (onReady).
 *
 * The naming work is opaque (two LLM calls), so the bar creeps toward 95%
 * on a timer and snaps to 100% when the polled naming_status flips to
 * 'done'. The real signal is naming_status; the percentage is cosmetic.
 */

import React, { useEffect, useState } from 'react';
import { Modal, Progress, Typography, Space, Button, Alert } from 'antd';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { scenariosApi } from '../../api/scenarios';

const { Text } = Typography;

export interface NamingProgressModalProps {
  scenarioId: string | null;
  /** Called when naming is done (or the user chooses to open anyway). */
  onReady: (scenarioId: string) => void;
  /** Called when the user backs out to the scenarios list. */
  onClose: () => void;
}

const NamingProgressModal: React.FC<NamingProgressModalProps> = ({
  scenarioId,
  onReady,
  onClose,
}) => {
  const queryClient = useQueryClient();
  const [pct, setPct] = useState(8);
  const [retrying, setRetrying] = useState(false);

  const { data } = useQuery({
    queryKey: ['scenario', scenarioId],
    queryFn: () => scenariosApi.get(scenarioId!),
    enabled: !!scenarioId,
    refetchInterval: (query) => {
      const status = query.state.data?.naming_status;
      return status === 'pending' || status === 'running' ? 2000 : false;
    },
  });

  const status = data?.naming_status;
  const inProgress = status === 'pending' || status === 'running';
  const failed = status === 'failed';

  // Creep the bar while naming is in progress.
  useEffect(() => {
    if (!scenarioId) {
      setPct(8);
      return;
    }
    if (!inProgress) return;
    const t = setInterval(() => {
      setPct((p) => (p < 95 ? Math.min(95, p + 3) : p));
    }, 4000);
    return () => clearInterval(t);
  }, [scenarioId, inProgress]);

  // When naming completes, snap to 100% and hand off to Studio.
  useEffect(() => {
    if (scenarioId && status === 'done') {
      setPct(100);
      onReady(scenarioId);
    }
  }, [scenarioId, status, onReady]);

  const handleRetry = async () => {
    if (!scenarioId) return;
    setRetrying(true);
    try {
      await scenariosApi.retryNaming(scenarioId);
      setPct(8);
      await queryClient.invalidateQueries({ queryKey: ['scenario', scenarioId] });
    } finally {
      setRetrying(false);
    }
  };

  return (
    <Modal
      open={!!scenarioId}
      title="Preparing your scenario"
      closable={false}
      maskClosable={false}
      keyboard={false}
      footer={
        failed
          ? [
              <Button key="close" onClick={onClose}>
                Back to scenarios
              </Button>,
              <Button
                key="open"
                onClick={() => scenarioId && onReady(scenarioId)}
              >
                Open anyway
              </Button>,
              <Button
                key="retry"
                type="primary"
                loading={retrying}
                onClick={handleRetry}
              >
                Retry naming
              </Button>,
            ]
          : [
              <Button key="open" onClick={() => scenarioId && onReady(scenarioId)}>
                Open without waiting
              </Button>,
            ]
      }
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {failed ? (
          <Alert
            type="warning"
            showIcon
            message="Device naming didn't finish"
            description="The scenario is built and usable with basic names. You can retry the descriptive naming or open it as-is."
          />
        ) : (
          <>
            <Text>
              Generating realistic, demo-friendly device names. This usually
              takes a minute or two — the Studio will open automatically when
              it's ready.
            </Text>
            <Progress percent={pct} status="active" showInfo={false} />
          </>
        )}
      </Space>
    </Modal>
  );
};

export default NamingProgressModal;
