/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * User management tab for admin settings — create / edit / promote / delete
 * users, reset passwords, and view a log of recent admin actions.
 */

import React, { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Checkbox,
  message,
  Tag,
  Popconfirm,
  Alert,
  Typography,
  Card,
} from 'antd';
import {
  LockOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UserOutlined,
  CrownOutlined,
  IdcardOutlined,
  UserAddOutlined,
  DeleteOutlined,
  MailOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  listUsers,
  resetUserPassword,
  toggleUserActive,
  createUser,
  updateUser,
  deleteUser,
  listUserAudit,
  type User,
  type UserAuditEntry,
} from '../../api/users';
import { useAuthStore } from '../../stores/authStore';
import { extractErrorMessage } from '../../utils/errorUtils';

const { Text } = Typography;

const UserManagementTab: React.FC = () => {
  const currentUser = useAuthStore((s) => s.user);
  const [users, setUsers] = useState<User[]>([]);
  const [audit, setAudit] = useState<UserAuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [resetForm] = Form.useForm();
  const [createForm] = Form.useForm();
  const [resetting, setResetting] = useState(false);
  const [creating, setCreating] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      setUsers(await listUsers());
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load users'));
    } finally {
      setLoading(false);
    }
  };

  const fetchAudit = async () => {
    try {
      setAudit(await listUserAudit(50));
    } catch {
      /* audit is best-effort; don't block the page */
    }
  };

  const refresh = () => {
    void fetchUsers();
    void fetchAudit();
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleToggleActive = async (user: User) => {
    try {
      await toggleUserActive(user.id);
      message.success(`User ${user.username} ${user.is_active ? 'deactivated' : 'activated'}`);
      refresh();
    } catch (err) {
      message.error(extractErrorMessage(err, 'Failed to update user status'));
    }
  };

  const handleToggleAdmin = async (user: User) => {
    try {
      await updateUser(user.id, { is_admin: !user.is_admin });
      message.success(`${user.username} ${user.is_admin ? 'is no longer an admin' : 'is now an admin'}`);
      refresh();
    } catch (err) {
      message.error(extractErrorMessage(err, 'Failed to change admin role'));
    }
  };

  const handleDelete = async (user: User) => {
    try {
      await deleteUser(user.id);
      message.success(`Deleted user ${user.username}`);
      refresh();
    } catch (err) {
      message.error(extractErrorMessage(err, 'Failed to delete user'));
    }
  };

  const handleResetPassword = (user: User) => {
    setSelectedUser(user);
    resetForm.resetFields();
    setResetModalOpen(true);
  };

  const handleResetSubmit = async (values: { newPassword: string }) => {
    if (!selectedUser) return;
    setResetting(true);
    try {
      await resetUserPassword(selectedUser.id, values.newPassword);
      message.success(`Password reset for ${selectedUser.username}`);
      setResetModalOpen(false);
      resetForm.resetFields();
      void fetchAudit();
    } catch (err) {
      message.error(extractErrorMessage(err, 'Failed to reset password'));
    } finally {
      setResetting(false);
    }
  };

  const handleCreateSubmit = async (values: {
    username: string;
    email?: string;
    password: string;
    is_admin?: boolean;
  }) => {
    setCreating(true);
    try {
      await createUser({
        username: values.username,
        email: values.email || null,
        password: values.password,
        is_admin: !!values.is_admin,
      });
      message.success(`Created user ${values.username}`);
      setCreateModalOpen(false);
      createForm.resetFields();
      refresh();
    } catch (err) {
      message.error(extractErrorMessage(err, 'Failed to create user'));
    } finally {
      setCreating(false);
    }
  };

  const columns: ColumnsType<User> = [
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
      render: (username: string, record: User) => (
        <Space>
          {record.is_admin ? (
            <CrownOutlined style={{ color: '#faad14' }} />
          ) : (
            <UserOutlined style={{ color: '#8c8c8c' }} />
          )}
          <Text strong>{username}</Text>
          {record.id === currentUser?.id && <Tag color="cyan">You</Tag>}
          {record.is_admin && <Tag color="gold">Admin</Tag>}
          {record.auth_source === 'ldap' ? (
            <Tag icon={<IdcardOutlined />} color="blue">
              LDAP
            </Tag>
          ) : (
            <Tag color="default">Local</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      render: (email: string) => email || <Text type="secondary">Not set</Text>,
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive: boolean) => (
        <Tag
          icon={isActive ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          color={isActive ? 'success' : 'default'}
        >
          {isActive ? 'Active' : 'Inactive'}
        </Tag>
      ),
    },
    {
      title: 'Last Login',
      dataIndex: 'last_login',
      key: 'last_login',
      render: (date: string) =>
        date ? new Date(date).toLocaleString() : <Text type="secondary">Never</Text>,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 320,
      render: (_, record: User) => {
        const isSelf = record.id === currentUser?.id;
        return (
          <Space wrap>
            {record.auth_source === 'local' && (
              <Button size="small" icon={<LockOutlined />} onClick={() => handleResetPassword(record)}>
                Reset Password
              </Button>
            )}
            <Popconfirm
              title={record.is_admin ? 'Revoke admin rights?' : 'Grant admin rights?'}
              onConfirm={() => handleToggleAdmin(record)}
              okText="Yes"
              cancelText="No"
              disabled={isSelf && record.is_admin}
            >
              <Button size="small" disabled={isSelf && record.is_admin}>
                {record.is_admin ? 'Revoke Admin' : 'Grant Admin'}
              </Button>
            </Popconfirm>
            <Popconfirm
              title={`${record.is_active ? 'Deactivate' : 'Activate'} user?`}
              description={
                record.is_active ? 'User will not be able to log in.' : 'User will be able to log in again.'
              }
              onConfirm={() => handleToggleActive(record)}
              okText="Yes"
              cancelText="No"
              disabled={isSelf}
            >
              <Button size="small" danger={record.is_active} disabled={isSelf}>
                {record.is_active ? 'Deactivate' : 'Activate'}
              </Button>
            </Popconfirm>
            <Popconfirm
              title="Delete this user?"
              description="Their scenarios and agents are kept (owner cleared). This cannot be undone."
              onConfirm={() => handleDelete(record)}
              okText="Delete"
              okButtonProps={{ danger: true }}
              cancelText="Cancel"
              disabled={isSelf}
            >
              <Button size="small" danger icon={<DeleteOutlined />} disabled={isSelf} />
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  const auditColumns: ColumnsType<UserAuditEntry> = [
    {
      title: 'When',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (d: string) => new Date(d).toLocaleString(),
    },
    { title: 'Actor', dataIndex: 'actor_username', key: 'actor', width: 140 },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
      width: 130,
      render: (a: string) => <Tag>{a}</Tag>,
    },
    { title: 'Target', dataIndex: 'target_username', key: 'target', width: 140 },
    {
      title: 'Detail',
      dataIndex: 'detail',
      key: 'detail',
      render: (d: string | null) => d || <Text type="secondary">—</Text>,
    },
  ];

  return (
    <div>
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

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary">Create, manage, and reset passwords for user accounts.</Text>
        <Button
          type="primary"
          icon={<UserAddOutlined />}
          onClick={() => {
            createForm.resetFields();
            setCreateModalOpen(true);
          }}
        >
          Create User
        </Button>
      </div>

      <Table columns={columns} dataSource={users} rowKey="id" loading={loading} pagination={false} size="small" />

      <Card title="Recent activity" size="small" style={{ marginTop: 24 }}>
        <Table
          columns={auditColumns}
          dataSource={audit}
          rowKey="id"
          pagination={{ pageSize: 8, hideOnSinglePage: true }}
          size="small"
          locale={{ emptyText: 'No user-management activity yet' }}
        />
      </Card>

      {/* Create User Modal */}
      <Modal
        title={
          <span>
            <UserAddOutlined style={{ marginRight: 8 }} />
            Create User
          </span>
        }
        open={createModalOpen}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        onOk={() => createForm.submit()}
        okText="Create"
        okButtonProps={{ loading: creating }}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreateSubmit}>
          <Form.Item
            name="username"
            label="Username"
            rules={[
              { required: true, message: 'Please enter a username' },
              { min: 3, message: 'At least 3 characters' },
            ]}
          >
            <Input prefix={<UserOutlined />} placeholder="username" autoComplete="off" />
          </Form.Item>
          <Form.Item name="email" label="Email (optional)" rules={[{ type: 'email', message: 'Invalid email' }]}>
            <Input prefix={<MailOutlined />} placeholder="user@example.com" autoComplete="off" />
          </Form.Item>
          <Form.Item
            name="password"
            label="Password"
            rules={[
              { required: true, message: 'Please enter a password' },
              { min: 8, message: 'At least 8 characters' },
              { max: 100, message: 'Less than 100 characters' },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="Min 8 characters" autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            name="confirmPassword"
            label="Confirm Password"
            dependencies={['password']}
            rules={[
              { required: true, message: 'Please confirm the password' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) return Promise.resolve();
                  return Promise.reject(new Error('Passwords do not match'));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="Confirm password" autoComplete="new-password" />
          </Form.Item>
          <Form.Item name="is_admin" valuePropName="checked">
            <Checkbox>Grant administrator privileges</Checkbox>
          </Form.Item>
        </Form>
      </Modal>

      {/* Reset Password Modal */}
      <Modal
        title={
          <span>
            <LockOutlined style={{ marginRight: 8 }} />
            Reset Password for {selectedUser?.username}
          </span>
        }
        open={resetModalOpen}
        onCancel={() => {
          setResetModalOpen(false);
          resetForm.resetFields();
        }}
        onOk={() => resetForm.submit()}
        okText="Reset Password"
        okButtonProps={{ loading: resetting }}
        destroyOnClose
      >
        <Alert
          message="This will reset the user's password without requiring their current password."
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form form={resetForm} layout="vertical" onFinish={handleResetSubmit}>
          <Form.Item
            name="newPassword"
            label="New Password"
            rules={[
              { required: true, message: 'Please enter a new password' },
              { min: 8, message: 'Password must be at least 8 characters' },
              { max: 100, message: 'Password must be less than 100 characters' },
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="Enter new password (min 8 characters)" />
          </Form.Item>
          <Form.Item
            name="confirmPassword"
            label="Confirm Password"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: 'Please confirm the password' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) return Promise.resolve();
                  return Promise.reject(new Error('Passwords do not match'));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="Confirm new password" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default UserManagementTab;
