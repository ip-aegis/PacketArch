/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Step 3: Device Count Selection
 */

import React from 'react';
import { Typography, Switch, Row, Col, Card, InputNumber, Slider, Space, Statistic } from 'antd';
import { RobotOutlined, DesktopOutlined } from '@ant-design/icons';
import { useAIScenarioWizardStore, DEVICE_TYPES_BY_VERTICAL } from '../../stores/aiScenarioWizardStore';

const { Title, Text, Paragraph } = Typography;

const DeviceCountStep: React.FC = () => {
  const {
    vertical,
    letAiDecideDevices,
    totalDeviceCount,
    deviceCounts,
    setLetAiDecideDevices,
    setTotalDeviceCount,
    setDeviceCount,
  } = useAIScenarioWizardStore();

  // Get device types for current vertical
  const deviceTypes = DEVICE_TYPES_BY_VERTICAL[vertical || 'manufacturing'] || [];

  // Calculate total from manual selection
  const manualTotal = Object.values(deviceCounts).reduce((a, b) => a + b, 0);

  return (
    <div>
      <Title level={4} style={{ color: '#e0e8f0', marginBottom: 8 }}>
        Configure Device Count
      </Title>

      <Paragraph style={{ color: '#8aa4bc', marginBottom: 24 }}>
        Specify how many devices should be in your scenario. You can let AI determine
        the optimal mix or manually select the number of each device type.
      </Paragraph>

      {/* AI Decision Toggle */}
      <Card
        style={{
          backgroundColor: letAiDecideDevices ? '#2a3f54' : '#1e2d3d',
          borderColor: letAiDecideDevices ? '#5a9fd4' : '#2a3f54',
          marginBottom: 24,
        }}
        styles={{ body: { padding: 16 } }}
      >
        <Space align="center">
          <Switch
            checked={letAiDecideDevices}
            onChange={setLetAiDecideDevices}
          />
          <RobotOutlined style={{ color: '#5a9fd4', fontSize: 20 }} />
          <div>
            <Text strong style={{ color: '#e0e8f0' }}>
              Let AI decide device mix
            </Text>
            <br />
            <Text style={{ color: '#8aa4bc', fontSize: 13 }}>
              Specify total count, AI determines the optimal mix based on your description and vertical
            </Text>
          </div>
        </Space>
      </Card>

      {/* AI Decides Mode: Total Count Slider */}
      {letAiDecideDevices && (
        <Card
          style={{
            backgroundColor: '#1e2d3d',
            borderColor: '#2a3f54',
          }}
          styles={{ body: { padding: 24 } }}
        >
          <div style={{ marginBottom: 16 }}>
            <Text style={{ color: '#e0e8f0', fontSize: 16 }}>Total Device Count</Text>
          </div>

          <Row gutter={24} align="middle">
            <Col span={16}>
              <Slider
                min={5}
                max={100}
                value={totalDeviceCount}
                onChange={setTotalDeviceCount}
                marks={{
                  5: '5',
                  20: '20',
                  50: '50',
                  100: '100',
                }}
                styles={{
                  track: { backgroundColor: '#5a9fd4' },
                  rail: { backgroundColor: '#2a3f54' },
                }}
              />
            </Col>
            <Col span={8}>
              <Statistic
                value={totalDeviceCount}
                suffix="devices"
                valueStyle={{ color: '#5a9fd4', fontSize: 28 }}
              />
            </Col>
          </Row>

          <div style={{ marginTop: 16 }}>
            <Text style={{ color: '#8aa4bc', fontSize: 13 }}>
              AI will create a realistic mix of PLCs, HMIs, sensors, and other devices
              appropriate for your selected vertical and description.
            </Text>
          </div>
        </Card>
      )}

      {/* Manual Selection Mode */}
      {!letAiDecideDevices && (
        <>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text style={{ color: '#8aa4bc' }}>
              Select device counts for each type (based on {vertical || 'manufacturing'} vertical)
            </Text>
            <Statistic
              title={<span style={{ color: '#8aa4bc', fontSize: 12 }}>Total</span>}
              value={manualTotal}
              suffix="/ 100"
              valueStyle={{
                color: manualTotal > 100 ? '#ff4d4f' : manualTotal > 0 ? '#52c41a' : '#8aa4bc',
                fontSize: 18,
              }}
            />
          </div>

          <Row gutter={[12, 12]}>
            {deviceTypes.map(deviceType => {
              const count = deviceCounts[deviceType.id] || 0;
              return (
                <Col span={12} key={deviceType.id}>
                  <Card
                    style={{
                      backgroundColor: count > 0 ? '#2a3f54' : '#1e2d3d',
                      borderColor: count > 0 ? '#5a9fd4' : '#2a3f54',
                      height: '100%',
                    }}
                    styles={{ body: { padding: 16 } }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ flex: 1 }}>
                        <Space align="center" style={{ marginBottom: 4 }}>
                          <DesktopOutlined style={{ color: count > 0 ? '#5a9fd4' : '#8aa4bc' }} />
                          <Text strong style={{ color: '#e0e8f0' }}>
                            {deviceType.name}
                          </Text>
                        </Space>
                        <br />
                        <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
                          {deviceType.description}
                        </Text>
                        <br />
                        <Text style={{ color: '#6b8399', fontSize: 11 }}>
                          Typical: {deviceType.range[0]}-{deviceType.range[1]}
                        </Text>
                      </div>
                      <InputNumber
                        min={0}
                        max={100}
                        value={count}
                        onChange={(value) => setDeviceCount(deviceType.id, value || 0)}
                        style={{ width: 70 }}
                        size="large"
                      />
                    </div>
                  </Card>
                </Col>
              );
            })}
          </Row>

          {manualTotal === 0 && (
            <Text style={{ color: '#faad14', marginTop: 16, display: 'block' }}>
              Please add at least one device
            </Text>
          )}

          {manualTotal > 100 && (
            <Text style={{ color: '#ff4d4f', marginTop: 16, display: 'block' }}>
              Total devices exceeds maximum of 100
            </Text>
          )}
        </>
      )}
    </div>
  );
};

export default DeviceCountStep;
