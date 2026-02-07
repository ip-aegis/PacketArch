/**
 * AgentInterfacesList - Displays the network interfaces reported by an agent.
 */

import React from 'react';
import {
  Card,
  Empty,
  List,
  Skeleton,
  Space,
  Typography,
} from 'antd';
import {
  ApiOutlined,
  DisconnectOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import type { AgentInterface } from '../../types/agent';

const { Text } = Typography;

export interface AgentInterfacesListProps {
  isOnline: boolean;
  isLoading: boolean;
  interfaces: AgentInterface[];
}

const AgentInterfacesList: React.FC<AgentInterfacesListProps> = React.memo(({
  isOnline,
  isLoading,
  interfaces,
}) => {
  return (
    <Card
      title={
        <Space>
          <GlobalOutlined />
          Network Interfaces
        </Space>
      }
      size="small"
    >
      {isLoading ? (
        <Skeleton active paragraph={{ rows: 3 }} />
      ) : interfaces.length > 0 ? (
        <List
          size="small"
          dataSource={interfaces}
          renderItem={(iface: AgentInterface) => (
            <List.Item>
              <List.Item.Meta
                avatar={<ApiOutlined />}
                title={
                  <Space>
                    <Text code>{iface.name}</Text>
                    {iface.mac && (
                      <Text type="secondary">({iface.mac})</Text>
                    )}
                  </Space>
                }
                description={
                  iface.error ? (
                    <Text type="danger">{iface.error}</Text>
                  ) : (
                    <Space direction="vertical" size={0}>
                      {iface.addresses.map((addr, idx) => (
                        <Text key={idx} type="secondary">
                          {addr.type.toUpperCase()}: {addr.address}
                          {addr.netmask && ` / ${addr.netmask}`}
                        </Text>
                      ))}
                      {iface.addresses.length === 0 && (
                        <Text type="secondary">No addresses</Text>
                      )}
                    </Space>
                  )
                }
              />
            </List.Item>
          )}
        />
      ) : isOnline ? (
        <Empty description="No interfaces available" />
      ) : (
        <Empty
          image={
            <DisconnectOutlined
              style={{ fontSize: 32, color: '#d9d9d9' }}
            />
          }
          description="Connect the agent to view interfaces"
        />
      )}
    </Card>
  );
});

AgentInterfacesList.displayName = 'AgentInterfacesList';

export default AgentInterfacesList;
