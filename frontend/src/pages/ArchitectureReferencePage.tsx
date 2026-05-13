/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import { useEffect, useState } from 'react';
import { Card, Col, Descriptions, Row, Select, Space, Table, Tabs, Tag, Typography, Alert } from 'antd';
import { architectureApi, type ArchetypeSummary, type CommMatrixEntrySummary, type RoleSummary } from '../api/architecture';

const { Title, Paragraph, Text } = Typography;

/**
 * Reference architecture browser. Renders the role catalog, archetypes,
 * and communication matrix per vertical so users can understand exactly
 * what the platform considers a rational OT environment for each
 * vertical they care about.
 */
const ArchitectureReferencePage = () => {
  const [verticals, setVerticals] = useState<string[]>([]);
  const [selectedVertical, setSelectedVertical] = useState<string | undefined>();
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [archetypes, setArchetypes] = useState<ArchetypeSummary[]>([]);
  const [matrixEntries, setMatrixEntries] = useState<CommMatrixEntrySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    architectureApi
      .getVerticals()
      .then((vs) => {
        setVerticals(vs);
        if (vs.length > 0 && !selectedVertical) {
          setSelectedVertical(vs[0]);
        }
      })
      .catch((e) => setError(`Failed to load verticals: ${e.message}`));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedVertical) return;
    setLoading(true);
    Promise.all([
      architectureApi.getRoles(selectedVertical),
      architectureApi.getArchetypes(selectedVertical),
      architectureApi.getCommMatrix(selectedVertical),
    ])
      .then(([r, a, m]) => {
        setRoles(r);
        setArchetypes(a);
        setMatrixEntries(m);
        setError(null);
      })
      .catch((e) => setError(`Failed to load architecture data: ${e.message}`))
      .finally(() => setLoading(false));
  }, [selectedVertical]);

  const verticalLabel = (v: string) =>
    v
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');

  const renderArchetype = (a: ArchetypeSummary) => (
    <Card
      key={a.id}
      title={a.name}
      style={{ marginBottom: 16 }}
      type="inner"
    >
      <Paragraph>{a.description}</Paragraph>
      <Descriptions size="small" column={2} bordered>
        <Descriptions.Item label="Vertical">{verticalLabel(a.vertical)}</Descriptions.Item>
        <Descriptions.Item label="Pattern">
          <Tag color="blue">{a.pattern}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Default vendor">
          <Tag>{a.default_vendor_profile}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Supported vendors">
          {a.supported_vendor_profiles.map((v) => (
            <Tag key={v}>{v}</Tag>
          ))}
        </Descriptions.Item>
      </Descriptions>

      <Title level={5} style={{ marginTop: 16 }}>
        Zone skeleton
      </Title>
      <Table
        size="small"
        dataSource={a.zones.map((z, i) => ({ key: i, ...z }))}
        pagination={false}
        columns={[
          { title: 'Zone ID', dataIndex: 'id', key: 'id' },
          { title: 'Name', dataIndex: 'name', key: 'name' },
          {
            title: 'Purdue Level',
            dataIndex: 'purdue_level',
            key: 'level',
            render: (lvl: number) => <Tag color="purple">L{lvl}</Tag>,
          },
          { title: 'Security', dataIndex: 'security_level', key: 'sec' },
          {
            title: 'Roles',
            key: 'roles',
            render: (_: unknown, z: ArchetypeSummary['zones'][number]) => (
              <Space wrap>
                {z.role_slots.map((s, i) => (
                  <Tag key={i}>{s.role_id}</Tag>
                ))}
              </Space>
            ),
          },
        ]}
      />

      <Title level={5} style={{ marginTop: 16 }}>
        Conduits (allowed cross-zone paths)
      </Title>
      <Table
        size="small"
        dataSource={a.conduits.map((c, i) => ({ key: i, ...c }))}
        pagination={false}
        columns={[
          { title: 'From', dataIndex: 'source_zone', key: 'src' },
          { title: 'To', dataIndex: 'target_zone', key: 'tgt' },
          { title: 'Direction', dataIndex: 'direction', key: 'dir' },
          {
            title: 'Allowed protocols',
            dataIndex: 'allowed_protocols',
            key: 'protos',
            render: (ps: string[]) => (
              <Space wrap>
                {ps.map((p) => (
                  <Tag key={p}>{p}</Tag>
                ))}
              </Space>
            ),
          },
        ]}
      />

      {a.notes.length > 0 && (
        <>
          <Title level={5} style={{ marginTop: 16 }}>
            Notes
          </Title>
          <ul>
            {a.notes.map((n, i) => (
              <li key={i}>
                <Text type="secondary">{n}</Text>
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  );

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>Architecture Reference</Title>
      <Paragraph>
        PacketArch encodes a typed reference architecture for each industrial vertical it supports.
        Templates and AI-generated scenarios materialize from the catalog below — you can see
        exactly what roles, archetypes, and communication patterns the platform considers a rational
        OT environment for each vertical.
      </Paragraph>

      {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} />}

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col>
          <Space>
            <Text strong>Vertical:</Text>
            <Select
              style={{ width: 280 }}
              value={selectedVertical}
              loading={loading}
              onChange={setSelectedVertical}
              options={verticals.map((v) => ({ value: v, label: verticalLabel(v) }))}
            />
          </Space>
        </Col>
      </Row>

      <Tabs
        items={[
          {
            key: 'archetypes',
            label: `Archetypes (${archetypes.length})`,
            children: <div>{archetypes.map(renderArchetype)}</div>,
          },
          {
            key: 'roles',
            label: `Roles (${roles.length})`,
            children: (
              <Table
                size="small"
                dataSource={roles.map((r, i) => ({ key: i, ...r }))}
                pagination={{ pageSize: 25 }}
                columns={[
                  { title: 'ID', dataIndex: 'id', key: 'id', width: 220 },
                  { title: 'Name', dataIndex: 'name', key: 'name' },
                  {
                    title: 'Purdue',
                    dataIndex: 'purdue_level',
                    key: 'lvl',
                    width: 80,
                    render: (lvl: number) => <Tag color="purple">L{lvl}</Tag>,
                  },
                  { title: 'Category', dataIndex: 'category', key: 'cat', width: 140 },
                  {
                    title: 'When to include',
                    dataIndex: 'when_to_include',
                    key: 'when',
                    render: (s: string) => <Text type="secondary">{s}</Text>,
                  },
                  {
                    title: 'Required protocols',
                    dataIndex: 'required_protocols',
                    key: 'req',
                    render: (ps: string[]) => (
                      <Space wrap size="small">
                        {ps.map((p) => (
                          <Tag color="red" key={p}>
                            {p}
                          </Tag>
                        ))}
                      </Space>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'matrix',
            label: `Comm Matrix (${matrixEntries.length})`,
            children: (
              <Table
                size="small"
                dataSource={matrixEntries.map((e, i) => ({ key: i, ...e }))}
                pagination={{ pageSize: 25 }}
                columns={[
                  { title: 'Source role', dataIndex: 'src_role', key: 'src' },
                  { title: 'Target role', dataIndex: 'tgt_role', key: 'tgt' },
                  { title: 'Pattern', dataIndex: 'pattern', key: 'pat', width: 130 },
                  {
                    title: 'Interval (ms)',
                    key: 'iv',
                    width: 130,
                    render: (_: unknown, e: CommMatrixEntrySummary) =>
                      e.interval_ms_min === e.interval_ms_max
                        ? `${e.interval_ms_min}`
                        : `${e.interval_ms_min}-${e.interval_ms_max}`,
                  },
                  {
                    title: 'Protocol options',
                    dataIndex: 'protocol_options',
                    key: 'protos',
                    render: (ps: string[]) => (
                      <Space wrap size="small">
                        {ps.map((p) => (
                          <Tag key={p}>{p}</Tag>
                        ))}
                      </Space>
                    ),
                  },
                  {
                    title: 'Description',
                    dataIndex: 'description',
                    key: 'desc',
                    render: (s: string) => <Text type="secondary">{s}</Text>,
                  },
                  {
                    title: 'Vertical',
                    dataIndex: 'vertical',
                    key: 'v',
                    width: 100,
                    render: (v: string) =>
                      v === '*' ? <Tag color="default">SHARED</Tag> : <Tag>{v}</Tag>,
                  },
                ]}
              />
            ),
          },
        ]}
      />
    </div>
  );
};

export default ArchitectureReferencePage;
