/**
 * Step 1 — Select an industry vertical.
 */

import React from 'react';
import { Row, Col, Card, Tag, Spin, Typography, Empty } from 'antd';
import { CheckCircleFilled } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { templatesApi } from '../../api/templates';
import { verticalConfig } from '../scenarios/scenarioConstants';
import { useGuidedBuilderStore } from '../../stores/guidedBuilderStore';

const { Text, Title } = Typography;

const VerticalSelectStep: React.FC = () => {
  const { selectedVertical, setSelectedVertical } = useGuidedBuilderStore();

  const { data: verticals, isLoading } = useQuery({
    queryKey: ['verticals'],
    queryFn: () => templatesApi.getVerticals(),
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!verticals || verticals.length === 0) {
    return <Empty description="No verticals available" />;
  }

  return (
    <div>
      <Title level={5} style={{ color: '#e0e8f0', marginBottom: 16 }}>
        Select an Industry Vertical
      </Title>
      <Text style={{ color: '#8aa4bc', display: 'block', marginBottom: 24 }}>
        Choose the industry that best matches your demo environment.
      </Text>

      <Row gutter={[16, 16]}>
        {verticals.map((v) => {
          const config = verticalConfig[v.id];
          const isDisabled = v.template_count === 0;
          const isSelected = selectedVertical === v.id;
          const color = config?.color ?? '#8c8c8c';

          return (
            <Col xs={24} sm={12} md={8} key={v.id}>
              <Card
                hoverable={!isDisabled}
                onClick={() => !isDisabled && setSelectedVertical(v.id)}
                style={{
                  borderColor: isSelected ? color : '#2a3f54',
                  borderWidth: isSelected ? 2 : 1,
                  backgroundColor: isSelected ? `${color}10` : '#141428',
                  opacity: isDisabled ? 0.45 : 1,
                  cursor: isDisabled ? 'not-allowed' : 'pointer',
                  position: 'relative',
                }}
                styles={{ body: { padding: '20px 16px', textAlign: 'center' } }}
              >
                {isSelected && (
                  <CheckCircleFilled
                    style={{
                      position: 'absolute',
                      top: 8,
                      right: 8,
                      color,
                      fontSize: 18,
                    }}
                  />
                )}
                <div style={{ fontSize: 28, color, marginBottom: 8 }}>
                  {config?.icon}
                </div>
                <div style={{ color: '#e0e8f0', fontWeight: 600, marginBottom: 4 }}>
                  {config?.label ?? v.name}
                </div>
                <Tag
                  color={isDisabled ? 'default' : undefined}
                  style={{ marginTop: 4 }}
                >
                  {v.template_count} template{v.template_count !== 1 ? 's' : ''}
                </Tag>
              </Card>
            </Col>
          );
        })}
      </Row>
    </div>
  );
};

export default VerticalSelectStep;
