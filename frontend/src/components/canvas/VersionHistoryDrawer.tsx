/**
 * Version History Drawer - Shows scenario version timeline with restore/compare actions
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Drawer,
  List,
  Tag,
  Button,
  Space,
  Typography,
  Popconfirm,
  Input,
  Pagination,
  Empty,
  Spin,
  App,
} from 'antd';
import {
  SaveOutlined,
  RollbackOutlined,
  DiffOutlined,
  EditOutlined,
  CheckOutlined,
  CloseOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import {
  scenarioVersionsApi,
  type VersionSummary,
} from '../../api/scenarioVersions';
import { extractErrorMessage } from '../../utils/errorUtils';
import VersionDiffModal from './VersionDiffModal';

const { Text } = Typography;

interface VersionHistoryDrawerProps {
  scenarioId: string | null;
  open: boolean;
  onClose: () => void;
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

function sourceColor(source: string): string {
  switch (source) {
    case 'manual':
      return 'blue';
    case 'auto':
      return 'default';
    case 'rollback':
      return 'orange';
    default:
      return 'default';
  }
}

function sourceLabel(source: string): string {
  switch (source) {
    case 'manual':
      return 'Manual';
    case 'auto':
      return 'Auto-saved';
    case 'rollback':
      return 'Pre-rollback';
    default:
      return source;
  }
}

const VersionHistoryDrawer: React.FC<VersionHistoryDrawerProps> = ({
  scenarioId,
  open,
  onClose,
}) => {
  const { message } = App.useApp();
  const [versions, setVersions] = useState<VersionSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [savingVersion, setSavingVersion] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState('');
  const [diffModalOpen, setDiffModalOpen] = useState(false);
  const [selectedVersionForDiff, setSelectedVersionForDiff] = useState<number | null>(null);

  const pageSize = 15;

  const fetchVersions = useCallback(async () => {
    if (!scenarioId) return;
    setLoading(true);
    try {
      const response = await scenarioVersionsApi.list(scenarioId, page, pageSize);
      setVersions(response.items);
      setTotal(response.total);
    } catch (error: unknown) {
      message.error(extractErrorMessage(error, 'Failed to load versions'));
    } finally {
      setLoading(false);
    }
  }, [scenarioId, page, message]);

  useEffect(() => {
    if (open && scenarioId) {
      setPage(1);
      fetchVersions();
    }
  }, [open, scenarioId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (open && scenarioId) {
      fetchVersions();
    }
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSaveVersion = async () => {
    if (!scenarioId) return;
    setSavingVersion(true);
    try {
      const version = await scenarioVersionsApi.create(scenarioId);
      message.success(`Version ${version.version_number} saved`);
      fetchVersions();
    } catch (error: unknown) {
      message.error(extractErrorMessage(error, 'Failed to save version'));
    } finally {
      setSavingVersion(false);
    }
  };

  const handleRestore = async (versionNumber: number) => {
    if (!scenarioId) return;
    try {
      const result = await scenarioVersionsApi.rollback(scenarioId, versionNumber);
      message.success(result.message);
      fetchVersions();
      // Reload the page to refresh the scenario canvas
      window.location.reload();
    } catch (error: unknown) {
      message.error(extractErrorMessage(error, 'Failed to restore version'));
    }
  };

  const handleUpdateLabel = async (versionId: string) => {
    if (!scenarioId) return;
    try {
      await scenarioVersionsApi.updateLabel(scenarioId, versionId, editLabel || null);
      setEditingId(null);
      fetchVersions();
    } catch (error: unknown) {
      message.error(extractErrorMessage(error, 'Failed to update label'));
    }
  };

  const handleDelete = async (versionId: string) => {
    if (!scenarioId) return;
    try {
      await scenarioVersionsApi.delete(scenarioId, versionId);
      message.success('Version deleted');
      fetchVersions();
    } catch (error: unknown) {
      message.error(extractErrorMessage(error, 'Failed to delete version'));
    }
  };

  const handleCompare = (versionNumber: number) => {
    setSelectedVersionForDiff(versionNumber);
    setDiffModalOpen(true);
  };

  return (
    <>
      <Drawer
        title="Version History"
        placement="right"
        width={480}
        onClose={onClose}
        open={open}
        styles={{
          header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
          body: { background: '#1a1a2e', padding: '16px' },
          content: { background: '#141428' },
        }}
        extra={
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSaveVersion}
            loading={savingVersion}
            size="small"
          >
            Save Version
          </Button>
        }
      >
        {loading && versions.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin />
          </div>
        ) : versions.length === 0 ? (
          <Empty
            description="No versions yet"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ color: '#6b6b8a' }}
          >
            <Button type="primary" onClick={handleSaveVersion}>
              Save First Version
            </Button>
          </Empty>
        ) : (
          <>
            <List
              dataSource={versions}
              loading={loading}
              renderItem={(v) => (
                <List.Item
                  style={{
                    background: '#141428',
                    borderRadius: 8,
                    marginBottom: 8,
                    padding: '12px 16px',
                    border: '1px solid #2d2d52',
                  }}
                >
                  <div style={{ width: '100%' }}>
                    {/* Header row */}
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 6,
                      }}
                    >
                      <Space size={8}>
                        <Text strong style={{ color: '#fff', fontSize: 14 }}>
                          v{v.version_number}
                        </Text>
                        <Tag color={sourceColor(v.source)} style={{ margin: 0 }}>
                          {sourceLabel(v.source)}
                        </Tag>
                      </Space>
                      <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                        {formatRelativeTime(v.created_at)}
                      </Text>
                    </div>

                    {/* Label */}
                    <div style={{ marginBottom: 6 }}>
                      {editingId === v.id ? (
                        <Space size={4}>
                          <Input
                            size="small"
                            value={editLabel}
                            onChange={(e) => setEditLabel(e.target.value)}
                            onPressEnter={() => handleUpdateLabel(v.id)}
                            placeholder="Version label..."
                            style={{
                              width: 200,
                              background: '#1a1a2e',
                              border: '1px solid #3a5068',
                              color: '#fff',
                            }}
                            autoFocus
                          />
                          <Button
                            size="small"
                            type="text"
                            icon={<CheckOutlined />}
                            onClick={() => handleUpdateLabel(v.id)}
                            style={{ color: '#52c41a' }}
                          />
                          <Button
                            size="small"
                            type="text"
                            icon={<CloseOutlined />}
                            onClick={() => setEditingId(null)}
                            style={{ color: '#6b6b8a' }}
                          />
                        </Space>
                      ) : (
                        <Space size={4}>
                          <Text style={{ color: v.label ? '#b8c9dc' : '#6b6b8a', fontSize: 13 }}>
                            {v.label || v.name}
                          </Text>
                          <Button
                            size="small"
                            type="text"
                            icon={<EditOutlined />}
                            onClick={() => {
                              setEditingId(v.id);
                              setEditLabel(v.label || '');
                            }}
                            style={{ color: '#6b6b8a' }}
                          />
                        </Space>
                      )}
                    </div>

                    {/* Stats */}
                    <div style={{ marginBottom: 8 }}>
                      <Space size={12}>
                        <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                          {v.device_count} devices
                        </Text>
                        <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                          {v.flow_count} flows
                        </Text>
                      </Space>
                    </div>

                    {/* Actions */}
                    <Space size={8}>
                      <Button
                        size="small"
                        icon={<DiffOutlined />}
                        onClick={() => handleCompare(v.version_number)}
                        style={{
                          background: '#253545',
                          borderColor: '#3a5068',
                          color: '#b8c9dc',
                        }}
                      >
                        Compare
                      </Button>
                      <Popconfirm
                        title={`Restore to v${v.version_number}?`}
                        description="A backup of the current state will be saved automatically."
                        onConfirm={() => handleRestore(v.version_number)}
                        okText="Restore"
                        cancelText="Cancel"
                      >
                        <Button
                          size="small"
                          icon={<RollbackOutlined />}
                          style={{
                            background: '#253545',
                            borderColor: '#3a5068',
                            color: '#b8c9dc',
                          }}
                        >
                          Restore
                        </Button>
                      </Popconfirm>
                      <Popconfirm
                        title="Delete this version?"
                        onConfirm={() => handleDelete(v.id)}
                        okText="Delete"
                        cancelText="Cancel"
                      >
                        <Button
                          size="small"
                          type="text"
                          icon={<DeleteOutlined />}
                          danger
                        />
                      </Popconfirm>
                    </Space>
                  </div>
                </List.Item>
              )}
            />
            {total > pageSize && (
              <div style={{ textAlign: 'center', marginTop: 12 }}>
                <Pagination
                  current={page}
                  pageSize={pageSize}
                  total={total}
                  onChange={setPage}
                  size="small"
                  showSizeChanger={false}
                />
              </div>
            )}
          </>
        )}
      </Drawer>

      {/* Diff Modal */}
      <VersionDiffModal
        scenarioId={scenarioId}
        open={diffModalOpen}
        onClose={() => {
          setDiffModalOpen(false);
          setSelectedVersionForDiff(null);
        }}
        initialBaseVersion={selectedVersionForDiff}
        versions={versions}
      />
    </>
  );
};

export default VersionHistoryDrawer;
