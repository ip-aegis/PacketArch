import React from 'react';
import { Empty, Button, Typography } from 'antd';
import { CloudServerOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;

const EmptyDashboard: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '80px 24px',
        background: '#1a1a2e',
        border: '1px solid #2d2d52',
        borderRadius: 8,
      }}
    >
      <Empty
        image={<CloudServerOutlined style={{ fontSize: 64, color: '#6b6b8a' }} />}
        description={false}
      />
      <Text style={{ color: '#fff', fontSize: 18, marginTop: 16 }}>
        No Active Deployments
      </Text>
      <Text type="secondary" style={{ marginTop: 8, marginBottom: 24 }}>
        Deploy a scenario to an agent to see live traffic metrics here.
      </Text>
      <Button type="primary" onClick={() => navigate('/deployments')}>
        Go to Deployments
      </Button>
    </div>
  );
};

export default EmptyDashboard;
