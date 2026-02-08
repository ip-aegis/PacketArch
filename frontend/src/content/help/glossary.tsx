/**
 * Glossary Help Article
 */

import React from 'react';
import { Typography, Space, Card, Divider, Input } from 'antd';
import { BookOutlined, SearchOutlined } from '@ant-design/icons';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, CARD_STYLE } from '../../constants/theme';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

interface GlossaryTerm {
  term: string;
  definition: string;
  category: 'protocol' | 'device' | 'network' | 'security' | 'general';
}

const glossaryTerms: GlossaryTerm[] = [
  // Protocols
  { term: 'Modbus TCP', definition: 'Industrial protocol for communication between PLCs and other devices over TCP/IP. Uses function codes to read/write registers and coils.', category: 'protocol' },
  { term: 'EtherNet/IP', definition: 'Industrial Ethernet protocol using CIP (Common Industrial Protocol) over standard Ethernet. Used by Rockwell/Allen-Bradley devices.', category: 'protocol' },
  { term: 'PROFINET', definition: 'Siemens industrial Ethernet standard for automation. Operates at Layer 2 with real-time capabilities.', category: 'protocol' },
  { term: 'CIP', definition: 'Common Industrial Protocol - application layer protocol used by EtherNet/IP, DeviceNet, and ControlNet.', category: 'protocol' },
  { term: 'DNP3', definition: 'Distributed Network Protocol - used in utilities for SCADA communication between control centers and remote stations.', category: 'protocol' },
  { term: 'IEC 104', definition: 'IEC 60870-5-104 - telecontrol protocol for power system SCADA over TCP/IP.', category: 'protocol' },
  { term: 'OPC UA', definition: 'Open Platform Communications Unified Architecture - platform-independent industrial communication standard.', category: 'protocol' },

  // Devices
  { term: 'PLC', definition: 'Programmable Logic Controller - industrial computer for automation control. Executes logic programs and controls I/O.', category: 'device' },
  { term: 'RTU', definition: 'Remote Terminal Unit - microprocessor-controlled device for remote monitoring and control in SCADA systems.', category: 'device' },
  { term: 'HMI', definition: 'Human-Machine Interface - operator interface panel for monitoring and controlling industrial processes.', category: 'device' },
  { term: 'VFD/Drive', definition: 'Variable Frequency Drive - motor controller that varies speed by adjusting electrical frequency.', category: 'device' },
  { term: 'I/O Module', definition: 'Input/Output module - expands PLC I/O capacity for connecting field devices.', category: 'device' },
  { term: 'Gateway', definition: 'Protocol converter that bridges different industrial networks or protocols.', category: 'device' },

  // Network
  { term: 'SCADA', definition: 'Supervisory Control and Data Acquisition - system for remote monitoring and control of industrial processes.', category: 'network' },
  { term: 'DCS', definition: 'Distributed Control System - control system with distributed controllers throughout a plant.', category: 'network' },
  { term: 'OT Network', definition: 'Operational Technology network - industrial network separate from IT/corporate networks.', category: 'network' },
  { term: 'DMZ', definition: 'Demilitarized Zone - network segment between OT and IT networks for controlled data exchange.', category: 'network' },
  { term: 'Purdue Model', definition: 'Reference architecture for industrial network segmentation with levels 0-5.', category: 'network' },

  // Security
  { term: 'CVE', definition: 'Common Vulnerabilities and Exposures - standardized identifier for security vulnerabilities.', category: 'security' },
  { term: 'CVSS', definition: 'Common Vulnerability Scoring System - numerical score (0-10) indicating vulnerability severity.', category: 'security' },
  { term: 'ICS', definition: 'Industrial Control System - general term for systems controlling industrial processes.', category: 'security' },
  { term: 'MITRE ATT&CK', definition: 'Framework of adversary tactics and techniques for cybersecurity threat modeling.', category: 'security' },

  // General
  { term: 'PCAP', definition: 'Packet Capture - file format for storing network traffic captures.', category: 'general' },
  { term: 'Fingerprint', definition: 'Unique identifier characteristics of a device based on protocol responses and behavior.', category: 'general' },
  { term: 'Polling', definition: 'Periodic requests from master to slave devices to read data or status.', category: 'general' },
  { term: 'Master/Slave', definition: 'Communication model where master initiates requests and slaves respond.', category: 'general' },
  { term: 'Function Code', definition: 'Modbus identifier specifying the operation type (read, write, diagnostic).', category: 'general' },
  { term: 'Register', definition: 'Memory location in a PLC/device that stores data values.', category: 'general' },
  { term: 'Coil', definition: 'Modbus term for a single-bit (on/off) data point.', category: 'general' },
];

const GlossaryContent: React.FC = () => {
  const [searchTerm, setSearchTerm] = React.useState('');

  const filteredTerms = glossaryTerms.filter(
    (t) =>
      t.term.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.definition.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const categoryColors: Record<string, string> = {
    protocol: ACCENT_BLUE,
    device: '#6CC04A',
    network: '#faad14',
    security: '#cf1322',
    general: TEXT_PARAGRAPH,
  };

  const groupedTerms = filteredTerms.reduce((acc, term) => {
    const firstLetter = term.term[0].toUpperCase();
    if (!acc[firstLetter]) acc[firstLetter] = [];
    acc[firstLetter].push(term);
    return acc;
  }, {} as Record<string, GlossaryTerm[]>);

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <BookOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Glossary
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          Reference guide for OT/ICS terminology, protocols, and concepts used throughout PacketArch.
        </Paragraph>
      </div>

      <Input
        prefix={<SearchOutlined style={{ color: '#6b6b8a' }} />}
        placeholder="Search terms..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        style={{
          ...CARD_STYLE,
          color: '#fff',
        }}
      />

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Text style={{ color: '#6b6b8a', fontSize: 12 }}>Categories:</Text>
        {Object.entries(categoryColors).map(([cat, color]) => (
          <Text key={cat} style={{ color, fontSize: 12, textTransform: 'capitalize' }}>
            {cat}
          </Text>
        ))}
      </div>

      {Object.entries(groupedTerms)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([letter, terms]) => (
          <Card
            key={letter}
            style={CARD_STYLE}
          >
            <Title level={5} style={{ color: ACCENT_BLUE, marginBottom: 16 }}>
              {letter}
            </Title>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              {terms.map((t) => (
                <div key={t.term}>
                  <Text
                    strong
                    style={{
                      color: categoryColors[t.category],
                      display: 'block',
                      marginBottom: 4,
                    }}
                  >
                    {t.term}
                  </Text>
                  <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
                    {t.definition}
                  </Paragraph>
                </div>
              ))}
            </Space>
          </Card>
        ))}

      {filteredTerms.length === 0 && (
        <Card style={CARD_STYLE}>
          <Text style={{ color: '#6b6b8a' }}>
            No terms found matching "{searchTerm}"
          </Text>
        </Card>
      )}
    </Space>
  );
};

export const glossaryArticle: HelpArticle = {
  id: 'glossary',
  title: 'Glossary',
  category: 'reference',
  keywords: [
    'glossary', 'terms', 'definitions', 'vocabulary', 'reference',
    'modbus', 'ethernet', 'profinet', 'plc', 'rtu', 'scada', 'ics', 'ot'
  ],
  summary: 'Reference guide for OT/ICS terminology, protocols, and industrial automation concepts.',
  content: GlossaryContent,
  relatedArticles: ['getting-started'],
  relatedPages: [],
  order: 1,
};
