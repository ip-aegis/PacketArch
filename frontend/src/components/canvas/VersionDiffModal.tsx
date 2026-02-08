/**
 * Version Diff Modal - Shows structured diff between two scenario versions
 */

import React, { useState, useCallback } from 'react';
import {
  Modal,
  Select,
  Button,
  Space,
  Typography,
  Tag,
  Collapse,
  Empty,
  Spin,
  App,
} from 'antd';
import {
  PlusCircleOutlined,
  MinusCircleOutlined,
  EditOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import {
  scenarioVersionsApi,
  type VersionSummary,
  type DiffEntry,
  type VersionDiffResponse,
} from '../../api/scenarioVersions';
import { extractErrorMessage } from '../../utils/errorUtils';

const { Text, Title } = Typography;

interface VersionDiffModalProps {
  scenarioId: string | null;
  open: boolean;
  onClose: () => void;
  initialBaseVersion: number | null;
  versions: VersionSummary[];
}

const categoryLabels: Record<string, string> = {
  devices: 'Devices',
  flows: 'Flows',
  zones: 'Zones',
  phases: 'Phases',
  metadata: 'Metadata',
};

const categoryOrder = ['devices', 'flows', 'zones', 'phases', 'metadata'];

function changeIcon(changeType: string) {
  switch (changeType) {
    case 'added':
      return <PlusCircleOutlined style={{ color: '#52c41a' }} />;
    case 'removed':
      return <MinusCircleOutlined style={{ color: '#ff4d4f' }} />;
    case 'modified':
      return <EditOutlined style={{ color: '#faad14' }} />;
    default:
      return null;
  }
}

function changeColor(changeType: string): string {
  switch (changeType) {
    case 'added':
      return '#52c41a';
    case 'removed':
      return '#ff4d4f';
    case 'modified':
      return '#faad14';
    default:
      return '#6b6b8a';
  }
}

const VersionDiffModal: React.FC<VersionDiffModalProps> = ({
  scenarioId,
  open,
  onClose,
  initialBaseVersion,
  versions,
}) => {
  const { message } = App.useApp();
  const [baseVersion, setBaseVersion] = useState<number | null>(null);
  const [compareVersion, setCompareVersion] = useState<number | null>(null);
  const [diffResult, setDiffResult] = useState<VersionDiffResponse | null>(null);
  const [loading, setLoading] = useState(false);

  // Set initial versions when modal opens
  React.useEffect(() => {
    if (open && initialBaseVersion !== null) {
      // Find the version before the selected one for comparison
      const sortedVersions = [...versions].sort(
        (a, b) => b.version_number - a.version_number
      );
      const idx = sortedVersions.findIndex(
        (v) => v.version_number === initialBaseVersion
      );
      const previousVersion =
        idx < sortedVersions.length - 1 ? sortedVersions[idx + 1] : null;

      setBaseVersion(previousVersion?.version_number ?? null);
      setCompareVersion(initialBaseVersion);
      setDiffResult(null);
    }
  }, [open, initialBaseVersion, versions]);

  const handleComputeDiff = useCallback(async () => {
    if (!scenarioId || baseVersion === null || compareVersion === null) return;
    if (baseVersion === compareVersion) {
      message.warning('Please select two different versions');
      return;
    }
    setLoading(true);
    try {
      const result = await scenarioVersionsApi.diff(
        scenarioId,
        baseVersion,
        compareVersion
      );
      setDiffResult(result);
    } catch (error: unknown) {
      message.error(extractErrorMessage(error, 'Failed to compute diff'));
    } finally {
      setLoading(false);
    }
  }, [scenarioId, baseVersion, compareVersion, message]);

  const handleSwapVersions = () => {
    setBaseVersion(compareVersion);
    setCompareVersion(baseVersion);
    setDiffResult(null);
  };

  // Group changes by category
  const groupedChanges: Record<string, DiffEntry[]> = {};
  if (diffResult) {
    for (const change of diffResult.changes) {
      if (!groupedChanges[change.category]) {
        groupedChanges[change.category] = [];
      }
      groupedChanges[change.category].push(change);
    }
  }

  const versionOptions = versions.map((v) => ({
    value: v.version_number,
    label: `v${v.version_number}${v.label ? ` — ${v.label}` : ''}`,
  }));

  return (
    <Modal
      title="Compare Versions"
      open={open}
      onCancel={() => {
        onClose();
        setDiffResult(null);
      }}
      footer={null}
      width={800}
      styles={{
        header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
        body: { background: '#1a1a2e', padding: 24, maxHeight: '70vh', overflowY: 'auto' },
        content: { background: '#141428' },
      }}
    >
      {/* Version selectors */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          marginBottom: 20,
        }}
      >
        <div style={{ flex: 1 }}>
          <Text style={{ color: '#6b6b8a', fontSize: 12, display: 'block', marginBottom: 4 }}>
            Base (older)
          </Text>
          <Select
            value={baseVersion}
            onChange={(v) => {
              setBaseVersion(v);
              setDiffResult(null);
            }}
            options={versionOptions}
            placeholder="Select base version"
            style={{ width: '100%' }}
          />
        </div>

        <Button
          type="text"
          icon={<SwapOutlined />}
          onClick={handleSwapVersions}
          style={{ marginTop: 20, color: '#6b6b8a' }}
        />

        <div style={{ flex: 1 }}>
          <Text style={{ color: '#6b6b8a', fontSize: 12, display: 'block', marginBottom: 4 }}>
            Compare (newer)
          </Text>
          <Select
            value={compareVersion}
            onChange={(v) => {
              setCompareVersion(v);
              setDiffResult(null);
            }}
            options={versionOptions}
            placeholder="Select compare version"
            style={{ width: '100%' }}
          />
        </div>

        <Button
          type="primary"
          onClick={handleComputeDiff}
          loading={loading}
          disabled={baseVersion === null || compareVersion === null}
          style={{ marginTop: 20 }}
        >
          Compare
        </Button>
      </div>

      {/* Diff results */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      ) : diffResult ? (
        <>
          {/* Summary bar */}
          <div
            style={{
              background: '#253545',
              borderRadius: 8,
              padding: '10px 16px',
              marginBottom: 16,
              border: '1px solid #3a5068',
            }}
          >
            <Space size={16}>
              {diffResult.summary.added > 0 && (
                <Text style={{ color: '#52c41a' }}>
                  +{diffResult.summary.added} added
                </Text>
              )}
              {diffResult.summary.removed > 0 && (
                <Text style={{ color: '#ff4d4f' }}>
                  -{diffResult.summary.removed} removed
                </Text>
              )}
              {diffResult.summary.modified > 0 && (
                <Text style={{ color: '#faad14' }}>
                  ~{diffResult.summary.modified} modified
                </Text>
              )}
              {diffResult.changes.length === 0 && (
                <Text style={{ color: '#6b6b8a' }}>No changes</Text>
              )}
            </Space>
          </div>

          {diffResult.changes.length === 0 ? (
            <Empty
              description="These versions are identical"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <Collapse
              defaultActiveKey={categoryOrder.filter((c) => groupedChanges[c])}
              ghost
              items={categoryOrder
                .filter((cat) => groupedChanges[cat])
                .map((cat) => ({
                  key: cat,
                  label: (
                    <Space>
                      <Title level={5} style={{ margin: 0, color: '#fff' }}>
                        {categoryLabels[cat] || cat}
                      </Title>
                      <Tag>{groupedChanges[cat].length}</Tag>
                    </Space>
                  ),
                  children: (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {groupedChanges[cat].map((change, idx) => (
                        <div
                          key={`${change.item_id || idx}`}
                          style={{
                            background: '#141428',
                            borderRadius: 6,
                            padding: '10px 14px',
                            border: `1px solid ${changeColor(change.change_type)}33`,
                            borderLeft: `3px solid ${changeColor(change.change_type)}`,
                          }}
                        >
                          <Space
                            style={{ marginBottom: change.details ? 8 : 0 }}
                          >
                            {changeIcon(change.change_type)}
                            <Text
                              style={{
                                color: changeColor(change.change_type),
                                fontWeight: 500,
                              }}
                            >
                              {change.change_type.charAt(0).toUpperCase() +
                                change.change_type.slice(1)}
                            </Text>
                            <Text style={{ color: '#b8c9dc' }}>
                              {change.item_name || change.item_id}
                            </Text>
                          </Space>

                          {/* Field-level details for modified items */}
                          {change.details &&
                            change.change_type === 'modified' &&
                            cat !== 'metadata' && (
                              <div style={{ paddingLeft: 24 }}>
                                {Object.entries(
                                  change.details as Record<
                                    string,
                                    { old?: unknown; new?: unknown; changed_subfields?: string[] }
                                  >
                                ).map(([field, detail]) => (
                                  <div
                                    key={field}
                                    style={{
                                      fontSize: 12,
                                      color: '#6b6b8a',
                                      marginBottom: 2,
                                    }}
                                  >
                                    <Text
                                      code
                                      style={{ color: '#b8c9dc', fontSize: 11 }}
                                    >
                                      {field}
                                    </Text>
                                    :{' '}
                                    {detail.changed_subfields ? (
                                      <Text style={{ color: '#faad14', fontSize: 12 }}>
                                        {detail.changed_subfields.join(', ')} changed
                                      </Text>
                                    ) : (
                                      <>
                                        <Text
                                          delete
                                          style={{ color: '#ff4d4f', fontSize: 12 }}
                                        >
                                          {String(detail.old ?? 'null')}
                                        </Text>
                                        {' → '}
                                        <Text style={{ color: '#52c41a', fontSize: 12 }}>
                                          {String(detail.new ?? 'null')}
                                        </Text>
                                      </>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}

                          {/* Metadata changes show old → new inline */}
                          {change.details && cat === 'metadata' && (
                            <div style={{ paddingLeft: 24 }}>
                              <Text
                                delete
                                style={{ color: '#ff4d4f', fontSize: 12 }}
                              >
                                {String(
                                  (change.details as Record<string, unknown>).old ?? 'null'
                                )}
                              </Text>
                              {' → '}
                              <Text style={{ color: '#52c41a', fontSize: 12 }}>
                                {String(
                                  (change.details as Record<string, unknown>).new ?? 'null'
                                )}
                              </Text>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ),
                }))}
            />
          )}
        </>
      ) : (
        <div style={{ textAlign: 'center', padding: 40, color: '#6b6b8a' }}>
          Select two versions and click Compare
        </div>
      )}
    </Modal>
  );
};

export default VersionDiffModal;
