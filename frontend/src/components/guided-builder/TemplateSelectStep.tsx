/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Step 2 — Select a template from the chosen vertical.
 */

import React from 'react';
import { Row, Col, Card, Tag, Spin, Typography, Empty } from 'antd';
import { CheckCircleFilled } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { templatesApi } from '../../api/templates';
import { useGuidedBuilderStore } from '../../stores/guidedBuilderStore';
import { PROTOCOL_COLORS } from '../../constants/protocols';

const { Text, Title, Paragraph } = Typography;

const TemplateSelectStep: React.FC = () => {
  const {
    selectedVertical,
    selectedTemplate,
    setSelectedTemplate,
    fetchTemplateDetail,
  } = useGuidedBuilderStore();

  const { data: templates, isLoading } = useQuery({
    queryKey: ['templates', selectedVertical],
    queryFn: () => templatesApi.list(selectedVertical || undefined),
    enabled: !!selectedVertical,
  });

  const handleSelect = (template: (typeof templates)[number]) => {
    setSelectedTemplate(template);
    if (selectedVertical) {
      fetchTemplateDetail(selectedVertical, template.name);
    }
  };

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!templates || templates.length === 0) {
    return <Empty description="No templates available for this vertical" />;
  }

  return (
    <div>
      <Title level={5} style={{ color: '#e0e8f0', marginBottom: 16 }}>
        Select a Template
      </Title>
      <Text style={{ color: '#8aa4bc', display: 'block', marginBottom: 24 }}>
        Pick a pre-built scenario template. You can review and customize devices in the next steps.
      </Text>

      <Row gutter={[16, 16]}>
        {templates.map((t) => {
          const isSelected = selectedTemplate?.name === t.name;

          return (
            <Col xs={24} sm={12} key={t.name}>
              <Card
                hoverable
                onClick={() => handleSelect(t)}
                style={{
                  borderColor: isSelected ? '#6CC04A' : '#2a3f54',
                  borderWidth: isSelected ? 2 : 1,
                  backgroundColor: isSelected ? '#6CC04A10' : '#141428',
                  position: 'relative',
                }}
                styles={{ body: { padding: 16 } }}
              >
                {isSelected && (
                  <CheckCircleFilled
                    style={{
                      position: 'absolute',
                      top: 8,
                      right: 8,
                      color: '#6CC04A',
                      fontSize: 18,
                    }}
                  />
                )}
                <div style={{ fontWeight: 600, color: '#e0e8f0', marginBottom: 6 }}>
                  {t.display_name}
                </div>
                <Paragraph
                  style={{ color: '#8aa4bc', fontSize: 13, marginBottom: 12 }}
                  ellipsis={{ rows: 2 }}
                >
                  {t.description}
                </Paragraph>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  <Tag>{t.device_count} devices</Tag>
                  {t.protocols.slice(0, 3).map((p) => (
                    <Tag key={p} color={PROTOCOL_COLORS[p as keyof typeof PROTOCOL_COLORS] ?? '#8c8c8c'}>
                      {p.replace(/_/g, ' ')}
                    </Tag>
                  ))}
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>
    </div>
  );
};

export default TemplateSelectStep;
