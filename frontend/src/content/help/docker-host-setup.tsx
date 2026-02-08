/**
 * Docker Host Setup Help Article
 * Comprehensive guide for preparing a Docker host for PacketArch traffic generation
 */

import React from 'react';
import { Typography, Space, Card, Tag, Divider, Alert, Steps, Table } from 'antd';
import {
  CloudServerOutlined,
  SafetyCertificateOutlined,
  ApiOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CodeOutlined,
  LockOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import { TEXT_PARAGRAPH, TEXT_BODY, ACCENT_BLUE, ACCENT_BLUE_HOVER, BORDER_DEFAULT, BG_INSET, CARD_STYLE, CODE_BLOCK_STYLE } from '../../constants/theme';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const CodeBlock: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <pre style={CODE_BLOCK_STYLE}>
    <code style={{ color: TEXT_BODY }}>{children}</code>
  </pre>
);

const DockerHostSetupContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <CloudServerOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Preparing a Docker Host for PacketArch
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          This guide walks you through preparing a Linux server to act as a Docker host
          for PacketArch traffic generation. The host will run the traffic generator
          container and inject packets onto your network.
        </Paragraph>
      </div>

      <Alert
        type="warning"
        showIcon
        icon={<WarningOutlined />}
        message="Security Considerations"
        description="Exposing the Docker API remotely requires careful security configuration. Always use TLS authentication in production environments."
        style={CARD_STYLE}
      />

      {/* Overview Steps */}
      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Setup Overview
        </Title>
        <Steps
          direction="vertical"
          size="small"
          current={-1}
          items={[
            { title: 'Install Docker Engine', description: 'Install Docker on the target host' },
            { title: 'Configure Docker for Remote Access', description: 'Enable TCP socket with TLS' },
            { title: 'Generate TLS Certificates', description: 'Create CA and client certificates' },
            { title: 'Configure Firewall', description: 'Allow Docker API port (2376)' },
            { title: 'Test Connectivity', description: 'Verify connection from PacketArch' },
          ]}
        />
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      {/* Step 1: Install Docker */}
      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <Tag color="blue">Step 1</Tag> Install Docker Engine
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Install Docker Engine on your Linux host. These instructions are for Ubuntu/Debian:
        </Paragraph>
        <CodeBlock>{`# Update package index
sudo apt-get update

# Install prerequisites
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin

# Verify installation
sudo docker run hello-world`}</CodeBlock>
        <Alert
          type="info"
          showIcon
          message="Other Distributions"
          description="For RHEL/CentOS, Fedora, or other distributions, see the official Docker documentation at docs.docker.com"
          style={{ ...CARD_STYLE, background: BG_INSET, marginTop: 12 }}
        />
      </Card>

      {/* Step 2: Generate Certificates */}
      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <Tag color="blue">Step 2</Tag> Generate TLS Certificates
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Generate certificates for secure Docker API access. Run these commands on the Docker host:
        </Paragraph>
        <CodeBlock>{`# Create certificate directory
sudo mkdir -p /etc/docker/certs
cd /etc/docker/certs

# Set your Docker host's IP or hostname
export DOCKER_HOST_IP="YOUR_HOST_IP"  # e.g., 10.10.20.113

# Generate CA private key
sudo openssl genrsa -aes256 -out ca-key.pem 4096
# Enter a passphrase when prompted

# Generate CA certificate
sudo openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca.pem \\
  -subj "/CN=Docker CA"

# Generate server private key
sudo openssl genrsa -out server-key.pem 4096

# Generate server CSR
sudo openssl req -subj "/CN=$DOCKER_HOST_IP" -sha256 -new \\
  -key server-key.pem -out server.csr

# Create server extensions file
echo "subjectAltName = IP:$DOCKER_HOST_IP,IP:127.0.0.1" | sudo tee extfile.cnf
echo "extendedKeyUsage = serverAuth" | sudo tee -a extfile.cnf

# Generate server certificate
sudo openssl x509 -req -days 365 -sha256 -in server.csr \\
  -CA ca.pem -CAkey ca-key.pem -CAcreateserial \\
  -out server-cert.pem -extfile extfile.cnf

# Generate client private key
sudo openssl genrsa -out key.pem 4096

# Generate client CSR
sudo openssl req -subj '/CN=client' -new -key key.pem -out client.csr

# Create client extensions file
echo "extendedKeyUsage = clientAuth" | sudo tee extfile-client.cnf

# Generate client certificate
sudo openssl x509 -req -days 365 -sha256 -in client.csr \\
  -CA ca.pem -CAkey ca-key.pem -CAcreateserial \\
  -out cert.pem -extfile extfile-client.cnf

# Set proper permissions
sudo chmod 0400 ca-key.pem key.pem server-key.pem
sudo chmod 0444 ca.pem server-cert.pem cert.pem

# Clean up CSR and temporary files
sudo rm -f server.csr client.csr extfile.cnf extfile-client.cnf`}</CodeBlock>
        <Alert
          type="success"
          showIcon
          icon={<SafetyCertificateOutlined />}
          message="Certificate Files for PacketArch"
          description={
            <Space direction="vertical" size="small">
              <Text style={{ color: TEXT_PARAGRAPH }}>Copy these files to use when adding the Docker host in PacketArch:</Text>
              <Text code style={{ color: TEXT_PARAGRAPH }}>ca.pem</Text>
              <Text style={{ color: '#6b6b8a' }}> - CA Certificate (paste into "CA Certificate" field)</Text>
              <br />
              <Text code style={{ color: TEXT_PARAGRAPH }}>cert.pem</Text>
              <Text style={{ color: '#6b6b8a' }}> - Client Certificate (paste into "Client Certificate" field)</Text>
              <br />
              <Text code style={{ color: TEXT_PARAGRAPH }}>key.pem</Text>
              <Text style={{ color: '#6b6b8a' }}> - Client Key (paste into "Client Key" field)</Text>
            </Space>
          }
          style={{ ...CARD_STYLE, background: BG_INSET, marginTop: 12 }}
        />
      </Card>

      {/* Step 3: Configure Docker Daemon */}
      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <Tag color="blue">Step 3</Tag> Configure Docker Daemon for Remote Access
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Configure Docker to listen on a TCP socket with TLS verification:
        </Paragraph>
        <CodeBlock>{`# Create or edit Docker daemon configuration
sudo mkdir -p /etc/docker
sudo nano /etc/docker/daemon.json`}</CodeBlock>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 12 }}>
          Add the following configuration:
        </Paragraph>
        <CodeBlock>{`{
  "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2376"],
  "tls": true,
  "tlscacert": "/etc/docker/certs/ca.pem",
  "tlscert": "/etc/docker/certs/server-cert.pem",
  "tlskey": "/etc/docker/certs/server-key.pem",
  "tlsverify": true
}`}</CodeBlock>
        <Alert
          type="warning"
          showIcon
          message="SystemD Override Required"
          description="Docker's systemd unit file may override the daemon.json hosts setting. Follow the next step to fix this."
          style={{ ...CARD_STYLE, background: BG_INSET, marginTop: 12 }}
        />
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 12 }}>
          Create a systemd override to prevent conflicts:
        </Paragraph>
        <CodeBlock>{`# Create systemd override directory
sudo mkdir -p /etc/systemd/system/docker.service.d

# Create override file
sudo nano /etc/systemd/system/docker.service.d/override.conf`}</CodeBlock>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 12 }}>
          Add these contents:
        </Paragraph>
        <CodeBlock>{`[Service]
ExecStart=
ExecStart=/usr/bin/dockerd`}</CodeBlock>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 12 }}>
          Reload and restart Docker:
        </Paragraph>
        <CodeBlock>{`# Reload systemd configuration
sudo systemctl daemon-reload

# Restart Docker
sudo systemctl restart docker

# Verify Docker is listening on port 2376
sudo netstat -tlnp | grep 2376
# Should show: tcp6  0  0 :::2376  :::*  LISTEN  .../dockerd`}</CodeBlock>
      </Card>

      {/* Step 4: Configure Firewall */}
      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <Tag color="blue">Step 4</Tag> Configure Firewall
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Allow incoming connections on port 2376 from the PacketArch server:
        </Paragraph>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 8 }}>
          <Text strong style={{ color: '#fff' }}>UFW (Ubuntu/Debian):</Text>
        </Paragraph>
        <CodeBlock>{`# Allow from specific IP (recommended)
sudo ufw allow from PACKETARCH_SERVER_IP to any port 2376

# Or allow from any (less secure)
sudo ufw allow 2376/tcp`}</CodeBlock>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 12 }}>
          <Text strong style={{ color: '#fff' }}>firewalld (RHEL/CentOS/Fedora):</Text>
        </Paragraph>
        <CodeBlock>{`# Allow Docker API port
sudo firewall-cmd --permanent --add-port=2376/tcp
sudo firewall-cmd --reload`}</CodeBlock>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 12 }}>
          <Text strong style={{ color: '#fff' }}>iptables:</Text>
        </Paragraph>
        <CodeBlock>{`# Allow from specific IP
sudo iptables -A INPUT -p tcp -s PACKETARCH_SERVER_IP --dport 2376 -j ACCEPT`}</CodeBlock>
      </Card>

      {/* Step 5: Test Connection */}
      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <Tag color="blue">Step 5</Tag> Test the Connection
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Test the connection locally on the Docker host first:
        </Paragraph>
        <CodeBlock>{`# Test local TLS connection
docker --tlsverify \\
  --tlscacert=/etc/docker/certs/ca.pem \\
  --tlscert=/etc/docker/certs/cert.pem \\
  --tlskey=/etc/docker/certs/key.pem \\
  -H=tcp://127.0.0.1:2376 \\
  version`}</CodeBlock>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 12 }}>
          From the PacketArch server (copy certificates first):
        </Paragraph>
        <CodeBlock>{`# Copy certificates to PacketArch server
scp user@DOCKER_HOST:/etc/docker/certs/ca.pem .
scp user@DOCKER_HOST:/etc/docker/certs/cert.pem .
scp user@DOCKER_HOST:/etc/docker/certs/key.pem .

# Test connection
docker --tlsverify \\
  --tlscacert=ca.pem \\
  --tlscert=cert.pem \\
  --tlskey=key.pem \\
  -H=tcp://DOCKER_HOST_IP:2376 \\
  version`}</CodeBlock>
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      {/* Adding to PacketArch */}
      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <SettingOutlined style={{ marginRight: 8 }} />
          Adding the Docker Host to PacketArch
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Once the Docker host is configured, add it in PacketArch:
        </Paragraph>
        <ol style={{ color: TEXT_PARAGRAPH, paddingLeft: 20 }}>
          <li>Go to <Text strong style={{ color: '#fff' }}>Settings</Text> &gt; <Text strong style={{ color: '#fff' }}>Docker Hosts</Text></li>
          <li>Click <Text strong style={{ color: '#fff' }}>Add Docker Host</Text></li>
          <li>Fill in the form:
            <ul style={{ marginTop: 8 }}>
              <li><Text strong style={{ color: '#fff' }}>Name:</Text> Friendly name (e.g., "Traffic Injector 1")</li>
              <li><Text strong style={{ color: '#fff' }}>Docker API URL:</Text> <Text code>tcp://DOCKER_HOST_IP:2376</Text></li>
              <li><Text strong style={{ color: '#fff' }}>TLS Enabled:</Text> Toggle ON</li>
              <li><Text strong style={{ color: '#fff' }}>CA Certificate:</Text> Paste contents of <Text code>ca.pem</Text></li>
              <li><Text strong style={{ color: '#fff' }}>Client Certificate:</Text> Paste contents of <Text code>cert.pem</Text></li>
              <li><Text strong style={{ color: '#fff' }}>Client Key:</Text> Paste contents of <Text code>key.pem</Text></li>
            </ul>
          </li>
          <li>Click <Text strong style={{ color: '#fff' }}>Create</Text></li>
          <li>Use <Text strong style={{ color: '#fff' }}>Test Connection</Text> to verify</li>
        </ol>
      </Card>

      {/* Network Interface Requirements */}
      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <GlobalOutlined style={{ marginRight: 8 }} />
          Network Interface Requirements
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          For live traffic injection, the Docker host needs:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
            <Text strong style={{ color: '#fff' }}>Physical network interface</Text>
            <Text style={{ color: '#6b6b8a' }}> connected to the target OT network</Text>
          </div>
          <div>
            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
            <Text strong style={{ color: '#fff' }}>Promiscuous mode</Text>
            <Text style={{ color: '#6b6b8a' }}> capability for packet capture/injection</Text>
          </div>
          <div>
            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
            <Text strong style={{ color: '#fff' }}>NET_ADMIN capability</Text>
            <Text style={{ color: '#6b6b8a' }}> for raw socket access (handled by container)</Text>
          </div>
        </Space>
        <CodeBlock>{`# List available network interfaces
ip link show

# Example interfaces:
# eth0 - Primary network interface
# ens192 - VMware virtual NIC
# enp3s0 - PCI Ethernet adapter`}</CodeBlock>
      </Card>

      {/* Troubleshooting */}
      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <WarningOutlined style={{ marginRight: 8, color: '#faad14' }} />
          Troubleshooting
        </Title>
        <Table
          size="small"
          pagination={false}
          dataSource={[
            {
              key: '1',
              issue: 'Connection refused',
              solution: 'Check Docker is listening: sudo netstat -tlnp | grep 2376',
            },
            {
              key: '2',
              issue: 'Certificate errors',
              solution: 'Verify cert paths in daemon.json match actual file locations',
            },
            {
              key: '3',
              issue: 'Permission denied',
              solution: 'Check certificate file permissions (400 for keys, 444 for certs)',
            },
            {
              key: '4',
              issue: 'Host unreachable',
              solution: 'Check firewall rules allow port 2376 from PacketArch server',
            },
            {
              key: '5',
              issue: 'Docker won\'t start',
              solution: 'Check logs: sudo journalctl -u docker.service -f',
            },
            {
              key: '6',
              issue: 'Interface not listed',
              solution: 'Ensure physical NIC is connected and up: ip link set eth0 up',
            },
          ]}
          columns={[
            {
              title: 'Issue',
              dataIndex: 'issue',
              width: '35%',
              render: (text) => <Text strong style={{ color: '#faad14' }}>{text}</Text>,
            },
            {
              title: 'Solution',
              dataIndex: 'solution',
              render: (text) => <Text style={{ color: TEXT_PARAGRAPH }}>{text}</Text>,
            },
          ]}
          style={{ background: 'transparent' }}
        />
      </Card>

      {/* Quick Reference */}
      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <CodeOutlined style={{ marginRight: 8 }} />
          Quick Reference
        </Title>
        <Table
          size="small"
          pagination={false}
          dataSource={[
            { key: '1', item: 'Default TLS Port', value: '2376' },
            { key: '2', item: 'Non-TLS Port (not recommended)', value: '2375' },
            { key: '3', item: 'Certificate Location', value: '/etc/docker/certs/' },
            { key: '4', item: 'Docker Config', value: '/etc/docker/daemon.json' },
            { key: '5', item: 'SystemD Override', value: '/etc/systemd/system/docker.service.d/override.conf' },
            { key: '6', item: 'Docker Logs', value: 'journalctl -u docker.service' },
          ]}
          columns={[
            {
              title: 'Item',
              dataIndex: 'item',
              width: '40%',
              render: (text) => <Text style={{ color: TEXT_PARAGRAPH }}>{text}</Text>,
            },
            {
              title: 'Value',
              dataIndex: 'value',
              render: (text) => <Text code style={{ color: ACCENT_BLUE_HOVER }}>{text}</Text>,
            },
          ]}
          style={{ background: 'transparent' }}
        />
      </Card>

      <Alert
        type="success"
        showIcon
        icon={<CheckCircleOutlined />}
        message="Ready for Deployment"
        description="Once the Docker host is added and tested successfully in PacketArch, you can select it when deploying scenarios to inject traffic onto your OT network."
        style={CARD_STYLE}
      />
    </Space>
  );
};

export const dockerHostSetupArticle: HelpArticle = {
  id: 'docker-host-setup',
  title: 'Docker Host Setup Guide',
  category: 'administration',
  keywords: [
    'docker', 'host', 'setup', 'configure', 'tls', 'certificate', 'ssl',
    'remote', 'api', 'tcp', 'firewall', 'install', 'preparation', 'traffic',
    'generator', 'deployment', 'network', 'interface', '2376', 'daemon',
    'systemd', 'ubuntu', 'linux', 'openssl'
  ],
  summary: 'Step-by-step guide to prepare a Linux server as a Docker host for PacketArch traffic generation, including TLS certificate setup and firewall configuration.',
  content: DockerHostSetupContent,
  relatedArticles: ['admin-settings', 'deployments'],
  relatedPages: ['/admin/settings'],
  order: 2,
};
