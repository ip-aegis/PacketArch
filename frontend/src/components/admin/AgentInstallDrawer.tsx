/**
 * AgentInstallDrawer - Installation Guide and Documentation
 *
 * Provides comprehensive documentation for installing and managing traffic agents:
 * - Prerequisites
 * - One-command installation
 * - Manual installation steps
 * - Configuration options
 * - Troubleshooting
 * - Upgrade and maintenance
 */

import React, { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Collapse,
  Divider,
  Drawer,
  message,
  Space,
  Steps,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CodeOutlined,
  CopyOutlined,
  DownloadOutlined,
  InfoCircleOutlined,
  RocketOutlined,
  SettingOutlined,
  ToolOutlined,
  WarningOutlined,
} from '@ant-design/icons';

const { Text, Title, Paragraph, Link } = Typography;
const { Panel } = Collapse;

interface AgentInstallDrawerProps {
  open: boolean;
  onClose: () => void;
}

const AgentInstallDrawer: React.FC<AgentInstallDrawerProps> = ({ open, onClose }) => {
  const serverUrl = `https://${window.location.hostname}`;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('Copied to clipboard');
  };

  const CodeBlock: React.FC<{ code: string; language?: string }> = ({ code, language = 'bash' }) => (
    <div style={{ position: 'relative', marginBottom: 16 }}>
      <pre
        style={{
          background: '#1e1e1e',
          color: '#d4d4d4',
          padding: 16,
          borderRadius: 6,
          overflow: 'auto',
          fontSize: 13,
          lineHeight: 1.5,
        }}
      >
        <code>{code}</code>
      </pre>
      <Button
        size="small"
        icon={<CopyOutlined />}
        style={{ position: 'absolute', top: 8, right: 8 }}
        onClick={() => copyToClipboard(code)}
      >
        Copy
      </Button>
    </div>
  );

  const envVarsData = [
    {
      key: 'PACKETARCH_SERVER',
      required: true,
      description: 'PacketArch server URL',
      example: serverUrl,
    },
    {
      key: 'AGENT_TOKEN',
      required: true,
      description: 'Authentication token from PacketArch',
      example: 'abc123...',
    },
    {
      key: 'DEFAULT_INTERFACE',
      required: false,
      description: 'Network interface for traffic injection',
      example: 'eth0',
    },
    {
      key: 'LOG_LEVEL',
      required: false,
      description: 'Logging verbosity',
      example: 'INFO',
    },
  ];

  const envVarsColumns = [
    {
      title: 'Variable',
      dataIndex: 'key',
      key: 'key',
      render: (text: string) => <Text code>{text}</Text>,
    },
    {
      title: 'Required',
      dataIndex: 'required',
      key: 'required',
      render: (required: boolean) =>
        required ? <Tag color="red">Required</Tag> : <Tag>Optional</Tag>,
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: 'Example',
      dataIndex: 'example',
      key: 'example',
      render: (text: string) => <Text type="secondary">{text}</Text>,
    },
  ];

  return (
    <Drawer
      title={
        <Space>
          <RocketOutlined />
          Traffic Agent Installation Guide
        </Space>
      }
      open={open}
      onClose={onClose}
      width={800}
    >
      <Tabs
        defaultActiveKey="quick"
        items={[
          {
            key: 'quick',
            label: (
              <span>
                <RocketOutlined /> Quick Start
              </span>
            ),
            children: (
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <Alert
                  message="Prerequisites"
                  description={
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      <li>Linux host (Ubuntu, Debian, CentOS, RHEL, Fedora)</li>
                      <li>Root or sudo access</li>
                      <li>Network access to PacketArch server</li>
                      <li>Docker will be installed automatically if not present</li>
                    </ul>
                  }
                  type="info"
                  showIcon
                />

                <Card title="Step 1: Create an Agent" size="small">
                  <Paragraph>
                    Click <Text strong>"Add Agent"</Text> in the Agents tab to create a new agent.
                    Save the authentication token - it's only shown once.
                  </Paragraph>
                </Card>

                <Card title="Step 2: Install on Remote Host" size="small">
                  <Paragraph>
                    Run this command on the target Linux host (replace{' '}
                    <Text code>YOUR_TOKEN</Text> with the token from step 1):
                  </Paragraph>

                  <CodeBlock
                    code={`curl -fsSLk ${serverUrl}/agent/install.sh | sudo bash -s -- \\
  --server ${serverUrl} \\
  --token "YOUR_TOKEN" \\
  --interface eth0 \\
  --insecure`}
                  />

                  <Alert
                    message="Self-Signed Certificate"
                    description={
                      <>
                        The <Text code>-k</Text> flag (curl) and <Text code>--insecure</Text> flag
                        (installer) skip SSL verification for self-signed certificates. Remove these
                        if using a valid SSL certificate.
                      </>
                    }
                    type="info"
                    showIcon
                    style={{ marginTop: 12, marginBottom: 12 }}
                  />

                  <Paragraph type="secondary">
                    Or register a new agent during installation (token will be created
                    automatically):
                  </Paragraph>

                  <CodeBlock
                    code={`curl -fsSLk ${serverUrl}/agent/install.sh | sudo bash -s -- \\
  --server ${serverUrl} \\
  --name "My-Agent" \\
  --register \\
  --insecure`}
                  />
                </Card>

                <Card title="Step 3: Verify Connection" size="small">
                  <Paragraph>
                    The agent should appear as <Tag color="green">Online</Tag> in the Agents tab
                    within a few seconds. Click on the agent to view details.
                  </Paragraph>
                </Card>

                <Alert
                  message="Auto-Updates Enabled"
                  description="Agents include Watchtower which automatically pulls new images. No manual updates required."
                  type="success"
                  showIcon
                  icon={<CheckCircleOutlined />}
                />
              </Space>
            ),
          },
          {
            key: 'manual',
            label: (
              <span>
                <ToolOutlined /> Manual Setup
              </span>
            ),
            children: (
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <Steps
                  direction="vertical"
                  items={[
                    {
                      title: 'Install Docker',
                      description: (
                        <CodeBlock code="curl -fsSL https://get.docker.com | sh" />
                      ),
                    },
                    {
                      title: 'Create Installation Directory',
                      description: (
                        <CodeBlock code="sudo mkdir -p /opt/packetarch-agent && cd /opt/packetarch-agent" />
                      ),
                    },
                    {
                      title: 'Create Environment File',
                      description: (
                        <>
                          <CodeBlock
                            code={`cat > .env << EOF
PACKETARCH_SERVER=${serverUrl}
AGENT_TOKEN=your_token_here
DEFAULT_INTERFACE=eth0
LOG_LEVEL=INFO
EOF`}
                          />
                          <Paragraph type="secondary">
                            Secure the file: <Text code>chmod 600 .env</Text>
                          </Paragraph>
                        </>
                      ),
                    },
                    {
                      title: 'Create Docker Compose File',
                      description: (
                        <CodeBlock
                          code={`cat > docker-compose.yml << 'EOF'
services:
  agent:
    image: ghcr.io/ip-aegis/packetarch-agent:latest
    container_name: packetarch-agent
    restart: unless-stopped
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_RAW
    env_file:
      - .env
    labels:
      - "com.centurylinklabs.watchtower.enable=true"

  watchtower:
    image: containrrr/watchtower
    container_name: packetarch-watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WATCHTOWER_CLEANUP=true
      - WATCHTOWER_POLL_INTERVAL=3600
      - WATCHTOWER_LABEL_ENABLE=true
EOF`}
                        />
                      ),
                    },
                    {
                      title: 'Start the Agent',
                      description: (
                        <CodeBlock code="docker compose up -d" />
                      ),
                    },
                  ]}
                />
              </Space>
            ),
          },
          {
            key: 'config',
            label: (
              <span>
                <SettingOutlined /> Configuration
              </span>
            ),
            children: (
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <Card title="Environment Variables" size="small">
                  <Table
                    columns={envVarsColumns}
                    dataSource={envVarsData}
                    rowKey="key"
                    pagination={false}
                    size="small"
                  />
                </Card>

                <Card title="Network Interface Selection" size="small">
                  <Paragraph>
                    The agent needs access to a network interface for traffic injection. Common
                    interface names:
                  </Paragraph>
                  <ul>
                    <li>
                      <Text code>eth0</Text> - Traditional ethernet
                    </li>
                    <li>
                      <Text code>ens192</Text> - VMware virtual NIC
                    </li>
                    <li>
                      <Text code>enp0s3</Text> - VirtualBox virtual NIC
                    </li>
                    <li>
                      <Text code>br0</Text> - Bridge interface
                    </li>
                  </ul>
                  <Paragraph>
                    List interfaces on the host: <Text code>ip link show</Text>
                  </Paragraph>
                </Card>

                <Card title="Docker Capabilities" size="small">
                  <Alert
                    message="Required Capabilities"
                    description={
                      <>
                        <Paragraph>
                          The agent requires <Text code>NET_ADMIN</Text> and{' '}
                          <Text code>NET_RAW</Text> capabilities for raw socket access (traffic
                          injection).
                        </Paragraph>
                        <Paragraph>
                          <Text code>network_mode: host</Text> is used to directly access host
                          network interfaces.
                        </Paragraph>
                      </>
                    }
                    type="warning"
                    showIcon
                    icon={<WarningOutlined />}
                  />
                </Card>
              </Space>
            ),
          },
          {
            key: 'manage',
            label: (
              <span>
                <CodeOutlined /> Management
              </span>
            ),
            children: (
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <Card title="Common Commands" size="small">
                  <Collapse ghost>
                    <Panel header="View Logs" key="logs">
                      <CodeBlock code="docker compose -f /opt/packetarch-agent/docker-compose.yml logs -f agent" />
                    </Panel>
                    <Panel header="Restart Agent" key="restart">
                      <CodeBlock code="docker compose -f /opt/packetarch-agent/docker-compose.yml restart agent" />
                    </Panel>
                    <Panel header="Stop Agent" key="stop">
                      <CodeBlock code="docker compose -f /opt/packetarch-agent/docker-compose.yml down" />
                    </Panel>
                    <Panel header="Start Agent" key="start">
                      <CodeBlock code="docker compose -f /opt/packetarch-agent/docker-compose.yml up -d" />
                    </Panel>
                    <Panel header="Check Status" key="status">
                      <CodeBlock code="docker compose -f /opt/packetarch-agent/docker-compose.yml ps" />
                    </Panel>
                    <Panel header="Update Manually" key="update">
                      <CodeBlock
                        code={`cd /opt/packetarch-agent
docker compose pull
docker compose up -d`}
                      />
                    </Panel>
                    <Panel header="Uninstall" key="uninstall">
                      <CodeBlock
                        code={`cd /opt/packetarch-agent
docker compose down
sudo rm -rf /opt/packetarch-agent`}
                      />
                    </Panel>
                  </Collapse>
                </Card>

                <Card title="Troubleshooting" size="small">
                  <Collapse ghost>
                    <Panel header="Agent won't connect" key="connect">
                      <ul>
                        <li>Verify the server URL is correct and accessible</li>
                        <li>Check that the token hasn't been regenerated</li>
                        <li>
                          Ensure firewall allows outbound HTTPS (443) or WebSocket
                        </li>
                        <li>
                          Check logs: <Text code>docker logs packetarch-agent</Text>
                        </li>
                      </ul>
                    </Panel>
                    <Panel header="Traffic not appearing" key="traffic">
                      <ul>
                        <li>Verify the correct network interface is configured</li>
                        <li>
                          Check interface exists: <Text code>ip link show</Text>
                        </li>
                        <li>Ensure the agent has NET_ADMIN and NET_RAW capabilities</li>
                        <li>Verify scenario devices have valid MAC/IP addresses</li>
                      </ul>
                    </Panel>
                    <Panel header="High CPU/Memory" key="resources">
                      <ul>
                        <li>
                          Large scenarios with many flows can be resource-intensive
                        </li>
                        <li>Check for scenarios with very low poll intervals</li>
                        <li>Consider distributing load across multiple agents</li>
                      </ul>
                    </Panel>
                    <Panel header="Connection drops frequently" key="drops">
                      <ul>
                        <li>Check network stability between agent and server</li>
                        <li>Look for firewall/proxy issues with WebSocket connections</li>
                        <li>Agent will auto-reconnect after 5 seconds</li>
                      </ul>
                    </Panel>
                  </Collapse>
                </Card>

                <Card title="Auto-Updates (Watchtower)" size="small">
                  <Paragraph>
                    The agent stack includes Watchtower for automatic updates. It checks for new
                    images every hour and updates automatically.
                  </Paragraph>
                  <ul>
                    <li>No downtime - containers are recreated with new images</li>
                    <li>Running scenarios will be stopped during update</li>
                    <li>
                      Disable auto-updates by removing the{' '}
                      <Text code>watchtower.enable</Text> label
                    </li>
                  </ul>
                </Card>
              </Space>
            ),
          },
        ]}
      />
    </Drawer>
  );
};

export default AgentInstallDrawer;
