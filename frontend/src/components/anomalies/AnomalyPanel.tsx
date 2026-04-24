/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Anomaly Panel - Browse anomaly templates and manage campaigns
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Card,
  Space,
  Typography,
  Tag,
  Button,
  Select,
  List,
  Empty,
  Collapse,
  Badge,
  Tooltip,
  message,
} from 'antd';
import {
  ThunderboltOutlined,
  FilterOutlined,
  ReloadOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  PlusOutlined,
  BugOutlined,
} from '@ant-design/icons';
import { PanelContainer, LoadingSpinner } from '../common';
import {
  listAnomalyTemplates,
  suggestAnomalies,
  type AnomalyTemplate,
  type SuggestedAnomaly,
} from '../../api/anomalies';

const { Text, Title } = Typography;
const { Panel } = Collapse;

interface AnomalyPanelProps {
  scenarioId: string | null;
  onCreateCampaign?: (templateIds: string[]) => void;
}

const categoryColors: Record<string, string> = {
  timing: 'blue',
  protocol: 'purple',
  sequence: 'cyan',
  payload: 'orange',
  network: 'green',
  security: 'red',
};

const severityColors: Record<string, string> = {
  low: 'default',
  medium: 'warning',
  high: 'orange',
  critical: 'error',
};

const AnomalyPanel: React.FC<AnomalyPanelProps> = ({
  scenarioId,
  onCreateCampaign,
}) => {
  const [templates, setTemplates] = useState<AnomalyTemplate[]>([]);
  const [suggestions, setSuggestions] = useState<SuggestedAnomaly[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
  const [selectedSeverity, setSelectedSeverity] = useState<string | undefined>();
  const [selectedTemplates, setSelectedTemplates] = useState<Set<string>>(new Set());

  // Fetch templates
  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listAnomalyTemplates({
        category: selectedCategory,
        severity: selectedSeverity,
      });
      setTemplates(data.templates);
      setCategories(data.categories);
    } catch (err) {
      console.error('Failed to fetch anomaly templates:', err);
      message.error('Failed to load anomaly templates');
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, selectedSeverity]);

  // Fetch suggestions for scenario
  const fetchSuggestions = useCallback(async () => {
    if (!scenarioId) return;

    setLoadingSuggestions(true);
    try {
      const data = await suggestAnomalies(scenarioId, 10);
      setSuggestions(data.suggestions);
    } catch (err) {
      console.error('Failed to fetch suggestions:', err);
      // Don't show error for suggestions - they're optional
    } finally {
      setLoadingSuggestions(false);
    }
  }, [scenarioId]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  // Toggle template selection
  const handleToggleTemplate = (templateId: string) => {
    setSelectedTemplates((prev) => {
      const next = new Set(prev);
      if (next.has(templateId)) {
        next.delete(templateId);
      } else {
        next.add(templateId);
      }
      return next;
    });
  };

  // Create campaign with selected templates
  const handleCreateCampaign = () => {
    if (selectedTemplates.size === 0) {
      message.warning('Select at least one anomaly template');
      return;
    }
    onCreateCampaign?.(Array.from(selectedTemplates));
  };

  // Group templates by category
  const templatesByCategory = templates.reduce((acc, template) => {
    const category = template.category;
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(template);
    return acc;
  }, {} as Record<string, AnomalyTemplate[]>);

  return (
    <PanelContainer padding={0}>
      {/* AI Suggestions */}
      {scenarioId && suggestions.length > 0 && (
        <Card
          size="small"
          title={
            <Space>
              <BugOutlined />
              <span>AI Suggestions</span>
              <Badge count={suggestions.length} style={{ backgroundColor: '#5a9fd4' }} />
            </Space>
          }
          style={{ background: '#1a2734' }}
          styles={{ body: { padding: '8px' } }}
        >
          {loadingSuggestions ? (
            <LoadingSpinner padding={12} size="small" />
          ) : (
            <List
              size="small"
              dataSource={suggestions.slice(0, 5)}
              renderItem={(suggestion) => (
                <List.Item
                  style={{
                    padding: '6px 8px',
                    background: '#0d1117',
                    borderRadius: 4,
                    marginBottom: 4,
                    cursor: 'pointer',
                    border: selectedTemplates.has(suggestion.template_id)
                      ? '1px solid #5a9fd4'
                      : '1px solid transparent',
                  }}
                  onClick={() => handleToggleTemplate(suggestion.template_id)}
                >
                  <Space direction="vertical" size={0} style={{ width: '100%' }}>
                    <Space size={4}>
                      <Text style={{ fontSize: 11, color: '#c9d1d9' }}>
                        {suggestion.name}
                      </Text>
                      <Tag
                        color={categoryColors[suggestion.category]}
                        style={{ fontSize: 9 }}
                      >
                        {suggestion.category}
                      </Tag>
                      <Tag
                        color={severityColors[suggestion.severity]}
                        style={{ fontSize: 9 }}
                      >
                        {suggestion.severity}
                      </Tag>
                    </Space>
                    <Space size={4} wrap>
                      {suggestion.reasons.slice(0, 2).map((reason, i) => (
                        <Text key={i} style={{ fontSize: 9, color: '#6a8caf' }}>
                          {reason}
                        </Text>
                      ))}
                    </Space>
                  </Space>
                </List.Item>
              )}
            />
          )}
        </Card>
      )}

      {/* Filters */}
      <Card
        size="small"
        title={
          <Space>
            <FilterOutlined />
            <span>Browse Templates</span>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '12px' } }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          <div style={{ display: 'flex', gap: 8 }}>
            <Select
              placeholder="Category"
              style={{ flex: 1 }}
              size="small"
              allowClear
              value={selectedCategory}
              onChange={setSelectedCategory}
              options={categories.map((c) => ({
                value: c,
                label: (
                  <Space>
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: categoryColors[c] || '#666',
                        display: 'inline-block',
                      }}
                    />
                    <span style={{ textTransform: 'capitalize' }}>{c}</span>
                  </Space>
                ),
              }))}
            />
            <Select
              placeholder="Severity"
              style={{ flex: 1 }}
              size="small"
              allowClear
              value={selectedSeverity}
              onChange={setSelectedSeverity}
              options={[
                { value: 'low', label: 'Low' },
                { value: 'medium', label: 'Medium' },
                { value: 'high', label: 'High' },
                { value: 'critical', label: 'Critical' },
              ]}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Text style={{ fontSize: 10, color: '#6a8caf' }}>
              {selectedTemplates.size} selected
            </Text>
            <Button
              type="text"
              size="small"
              icon={<ReloadOutlined />}
              onClick={fetchTemplates}
            >
              Refresh
            </Button>
          </div>
        </Space>
      </Card>

      {/* Templates by Category */}
      <Card
        size="small"
        title={
          <Space>
            <ThunderboltOutlined />
            <span>Anomaly Templates</span>
            <Tag>{templates.length}</Tag>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '8px' } }}
      >
        {loading ? (
          <LoadingSpinner />
        ) : templates.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Text style={{ color: '#6a8caf', fontSize: 11 }}>
                No anomaly templates found
              </Text>
            }
          />
        ) : (
          <Collapse
            ghost
            expandIconPosition="start"
            style={{ background: 'transparent' }}
          >
            {Object.entries(templatesByCategory).map(([category, categoryTemplates]) => (
              <Panel
                key={category}
                header={
                  <Space>
                    <Tag
                      color={categoryColors[category]}
                      style={{ fontSize: 10, textTransform: 'capitalize' }}
                    >
                      {category}
                    </Tag>
                    <Text style={{ fontSize: 11, color: '#8aa4bc' }}>
                      {categoryTemplates.length} templates
                    </Text>
                  </Space>
                }
                style={{ marginBottom: 4 }}
              >
                <List
                  size="small"
                  dataSource={categoryTemplates}
                  renderItem={(template) => (
                    <AnomalyTemplateItem
                      key={template.id}
                      template={template}
                      selected={selectedTemplates.has(template.id)}
                      onToggle={() => handleToggleTemplate(template.id)}
                    />
                  )}
                />
              </Panel>
            ))}
          </Collapse>
        )}
      </Card>

      {/* Create Campaign Button */}
      {selectedTemplates.size > 0 && (
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleCreateCampaign}
          block
        >
          Create Campaign ({selectedTemplates.size} anomalies)
        </Button>
      )}
    </PanelContainer>
  );
};

// Anomaly Template Item Component
interface AnomalyTemplateItemProps {
  template: AnomalyTemplate;
  selected: boolean;
  onToggle: () => void;
}

const AnomalyTemplateItem: React.FC<AnomalyTemplateItemProps> = ({
  template,
  selected,
  onToggle,
}) => {
  return (
    <div
      style={{
        padding: '8px',
        background: '#0d1117',
        borderRadius: 4,
        marginBottom: 4,
        cursor: 'pointer',
        border: selected ? '1px solid #5a9fd4' : '1px solid transparent',
      }}
      onClick={onToggle}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Space direction="vertical" size={2}>
          <Space size={4}>
            <Text style={{ fontSize: 11, color: '#c9d1d9', fontWeight: 500 }}>
              {template.name}
            </Text>
            <Tag
              color={severityColors[template.severity]}
              style={{ fontSize: 9 }}
            >
              {template.severity}
            </Tag>
          </Space>
          {template.description && (
            <Text
              style={{ fontSize: 10, color: '#6a8caf' }}
              ellipsis={{ tooltip: template.description }}
            >
              {template.description}
            </Text>
          )}
          <Space size={4} wrap>
            {template.target_protocols?.map((proto) => (
              <Tag key={proto} style={{ fontSize: 9 }}>
                {proto}
              </Tag>
            ))}
            {template.target_device_types?.map((type) => (
              <Tag key={type} color="cyan" style={{ fontSize: 9 }}>
                {type}
              </Tag>
            ))}
          </Space>
        </Space>
        <div
          style={{
            width: 16,
            height: 16,
            borderRadius: '50%',
            background: selected ? '#5a9fd4' : '#2a3f54',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 10,
            color: selected ? '#fff' : '#6a8caf',
          }}
        >
          {selected ? '✓' : '○'}
        </div>
      </div>
    </div>
  );
};

export default AnomalyPanel;
