/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * PacketArch Mimic — Device Emulation Help Article
 */

import React from 'react';
import { Typography, Space, Card, Alert, Tag } from 'antd';
import {
  ApiOutlined,
  ExperimentOutlined,
  PartitionOutlined,
  DeploymentUnitOutlined,
} from '@ant-design/icons';
import type { HelpArticle } from './index';
import { TEXT_PARAGRAPH, ACCENT_BLUE, CARD_STYLE, CODE_BLOCK_STYLE } from '../../constants/theme';

const { Title, Paragraph, Text } = Typography;

const MimicContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <ExperimentOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Mimic — Device Emulation
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          Mimic is a separate path from scenario traffic generation. A scenario
          <Text style={{ color: '#fff' }}> replays</Text> traffic onto the wire; a Mimic
          persona <Text style={{ color: '#fff' }}>binds a real socket</Text> and answers
          like the device it imitates. A scanner, an HMI, or a Cyber Vision sensor can
          talk to it and get real protocol responses back, because there is a live
          server on the other end rather than a recording.
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        message="Off by default"
        description="Mimic is gated by the mimic_enabled feature flag, which defaults to false. When it is off, these routes redirect and the API returns 503."
      />

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          When to use Mimic instead of a scenario
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Paragraph style={{ color: TEXT_PARAGRAPH, margin: 0 }}>
            <Tag color="blue">Use Mimic</Tag>
            when something needs to <Text style={{ color: '#fff' }}>interrogate</Text> a
            device — an active scanner, a discovery tool, an HMI you want to point at a
            PLC, or deep-packet inspection that reads identity objects. Mimic answers
            reads and writes, so an OPC UA browse or a Modbus FC43 identity request
            returns real data.
          </Paragraph>
          <Paragraph style={{ color: TEXT_PARAGRAPH, margin: 0 }}>
            <Tag color="green">Use a scenario</Tag>
            when you need <Text style={{ color: '#fff' }}>volume and breadth</Text> — many
            devices, many protocols, PCAP output, attack playbooks, timing realism. A
            scenario does not bind sockets and cannot be polled.
          </Paragraph>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <PartitionOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Cells
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          A <Text style={{ color: '#fff' }}>cell</Text> is the unit of deployment: one or
          more personas that share a network segment and can poll each other. The Mimic
          page lists your cells and their state, and deploys new ones from a device
          preset. Personas inside a cell take on the same vendor fingerprints the device
          library uses, so their MAC OUI, identity strings and firmware match the device
          they claim to be.
        </Paragraph>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
          Personas can be passive (answer when polled) or active — an HMI persona will
          poll a PLC persona over that PLC's native protocol, so the segment carries
          real request/response traffic with no generator involved.
        </Paragraph>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Protocols and live process values
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Four protocol servers are implemented: <Text code>Modbus TCP</Text>,
          <Text code> OPC UA</Text>, <Text code>BACnet</Text> and
          <Text code> IEC 60870-5-104</Text>.
        </Paragraph>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
          Registers and nodes are not static. Attach a process model and the values move
          under closed-loop PI control, so a trend read from a Mimic persona behaves like
          a plant rather than a counter. The library includes tank, tank control, chemical
          reactor, heat exchanger, compressor station, pump station and power feeder
          models. Writing a setpoint through a protocol client changes the loop, and the
          values that come back reflect it.
        </Paragraph>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <DeploymentUnitOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Where a cell runs
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="blue">On-box — Local Lab</Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 8, marginBottom: 0 }}>
              Personas run on the PacketArch host inside an isolated segment, mirrored to
              the Local Lab's Cyber Vision sensor. Pick an existing Local Lab as the
              target. This needs the host-agent running — the page says so when it is not.
            </Paragraph>
          </div>
          <div>
            <Tag color="purple">Off-box — CML</Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 8, marginBottom: 0 }}>
              Personas run on bare Cisco Modeling Labs nodes with no Docker and no
              dependencies to install, using a self-contained slim runtime. Identity is
              resolved at deploy time, so a node becomes a specific vendor and model when
              the cell lands on it rather than being baked into an image.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <ApiOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Mimic Studio
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          The presets on the Mimic page cover the common cases. Mimic Studio is the canvas
          for building a cell device by device: name each device, give it a role
          (PLC, HMI, RTU, …), choose the process model that drives its live values, and
          wire the polling relationships between them. Build the cell, then deploy it to
          a target Local Lab.
        </Paragraph>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
          A certification gate runs before deploy: Studio only offers to deploy a cell
          whose personas look like real devices — fingerprint, identity and protocol
          coherence all resolved. A cell that would present as an implausible device is
          blocked rather than shipped.
        </Paragraph>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Verifying a cell is convincing
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          The test that matters is whether a real tool is fooled. Point a scanner or a
          protocol client at a persona's address and confirm the answers:
        </Paragraph>
        <div style={CODE_BLOCK_STYLE}>
          nmap -sV -p 502 &lt;persona-ip&gt;{'\n'}
          # Modbus identity (FC43) should report the vendor and model{'\n'}
          # the persona claims, not a generic Modbus server
        </div>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 12, marginBottom: 0 }}>
          On a cell mirrored to a Cyber Vision sensor, CV should classify the persona as
          the device it imitates and populate vendor, model and firmware from the traffic
          alone. That is the pass condition — not that packets appeared, but that the
          product in the path drew the right conclusion from them.
        </Paragraph>
      </Card>
    </Space>
  );
};

export const mimicArticle: HelpArticle = {
  id: 'mimic',
  title: 'Mimic — Device Emulation',
  category: 'traffic-generation',
  keywords: [
    'mimic', 'emulation', 'emulate', 'persona', 'personas', 'cell', 'cells',
    'bind', 'socket', 'server', 'responder', 'scanner', 'nmap', 'poll',
    'modbus', 'opc ua', 'opcua', 'bacnet', 'iec 104', 'iec-104',
    'process model', 'pi control', 'closed loop', 'setpoint',
    'studio', 'canvas', 'cml', 'slim', 'local lab', 'certification',
  ],
  summary:
    'Emulate real devices that bind sockets and answer scanners, HMIs and Cyber Vision — on-box or on bare CML nodes.',
  content: MimicContent,
  relatedArticles: ['agents-hub', 'local-sensor-labs-scaling', 'cyber-vision', 'device-library'],
  relatedPages: ['/mimic', '/mimic/studio'],
  order: 5,
};
