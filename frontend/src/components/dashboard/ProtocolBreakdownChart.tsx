import React from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { DashboardProtocolStats } from '../../api/dashboard';
import { getProtocolColor, getProtocolLabel } from '../../constants/protocols';

interface ProtocolBreakdownChartProps {
  breakdown: Record<string, DashboardProtocolStats> | null;
}

const ProtocolBreakdownChart: React.FC<ProtocolBreakdownChartProps> = ({ breakdown }) => {
  if (!breakdown || Object.keys(breakdown).length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '20px 0', color: '#6b6b8a' }}>
        No protocol data
      </div>
    );
  }

  const data = Object.entries(breakdown).map(([protocol, stats]) => ({
    name: getProtocolLabel(protocol),
    value: stats.packets,
    color: getProtocolColor(protocol),
    bytes: stats.bytes,
    flows: stats.flow_count,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={40}
          outerRadius={70}
          dataKey="value"
          stroke="none"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: '#1a1a2e',
            border: '1px solid #2d2d52',
            borderRadius: 6,
            color: '#fff',
          }}
          formatter={(value: number, name: string) => [`${value.toLocaleString()} pkts`, name]}
        />
        <Legend
          wrapperStyle={{ color: '#6b6b8a', fontSize: 12 }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default ProtocolBreakdownChart;
