/**
 * User management tab for admin settings
 */

import React, { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  message,
  Tag,
  Popconfirm,
  Alert,
  Typography,
} from 'antd';
import {
  LockOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  UserOutlined,
  CrownOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  listUsers,
  resetUserPassword,
  toggleUserActive,
  type User,
} from '../../api/users';

const { Text } = Typography;

const UserManagementTab: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetModalOpen, setResetModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [form] = Form.useForm();
  const [resetting, setResetting] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listUsers();
      setUsers(data);
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : 'Failed to load users';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleToggleActive = async (user: User) => {
    try {
      await toggleUserActive(user.id);
      message.success(
        `User ${user.username} ${user.is_active ? 'deactivated' : 'activated'}`
      );
      fetchUsers();
    } catch (err) {
      message.error('Failed to update user status');
    }
  };

  const handleResetPassword = (user: User) => {
    setSelectedUser(user);
    form.resetFields();
    setResetModalOpen(true);
  };

  const handleResetSubmit = async (values: { newPassword: string }) => {
    if (!selectedUser) return;

    setResetting(true);
    try {
      await resetUserPassword(selectedUser.id, values.newPassword);
      message.success(`Password reset for ${selectedUser.username}`);
      setResetModalOpen(false);
      form.resetFields();
    } catch (err) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : (err as { response?: { data?: { detail?: string } } })?.response
              ?.data?.detail || 'Failed to reset password';
      message.error(errorMessage);
    } finally {
      setResetting(false);
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
          {record.is_admin && (
            <Tag color="gold">Admin</Tag>
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
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
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
      width: 200,
      render: (_, record: User) => (
        <Space>
          <Button
            size="small"
            icon={<LockOutlined />}
            onClick={() => handleResetPassword(record)}
          >
            Reset Password
          </Button>
          {!record.is_admin && (
            <Popconfirm
              title={`${record.is_active ? 'Deactivate' : 'Activate'} user?`}
              description={
                record.is_active
                  ? 'User will not be able to log in.'
                  : 'User will be able to log in again.'
              }
              onConfirm={() => handleToggleActive(record)}
              okText="Yes"
              cancelText="No"
            >
              <Button
                size="small"
                danger={record.is_active}
                type={record.is_active ? 'default' : 'primary'}
              >
                {record.is_active ? 'Deactivate' : 'Activate'}
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
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

      <div style={{ marginBottom: 16 }}>
        <Text type="secondary">
          Manage user accounts and reset passwords.
        </Text>
      </div>

      <Table
        columns={columns}
        dataSource={users}
        rowKey="id"
        loading={loading}
        pagination={false}
        size="small"
      />

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
          form.resetFields();
        }}
        onOk={() => form.submit()}
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

        <Form form={form} layout="vertical" onFinish={handleResetSubmit}>
          <Form.Item
            name="newPassword"
            label="New Password"
            rules={[
              { required: true, message: 'Please enter a new password' },
              { min: 8, message: 'Password must be at least 8 characters' },
              { max: 100, message: 'Password must be less than 100 characters' },
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Enter new password (min 8 characters)"
            />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            label="Confirm Password"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: 'Please confirm the password' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('Passwords do not match'));
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Confirm new password"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default UserManagementTab;
