/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import type { DashboardTimeSeriesPoint } from '../../api/dashboard';

interface PacketRateSparklineProps {
  timeSeries: DashboardTimeSeriesPoint[];
}

const PacketRateSparkline: React.FC<PacketRateSparklineProps> = ({ timeSeries }) => {
  if (timeSeries.length < 2) {
    return (
      <div style={{ textAlign: 'center', padding: '20px 0', color: '#6b6b8a' }}>
        Collecting data...
      </div>
    );
  }

  // Format time labels as relative (e.g., "2m ago")
  const data = timeSeries.map((point) => {
    const date = new Date(point.t);
    const secsAgo = Math.round((Date.now() - date.getTime()) / 1000);
    const label = secsAgo > 60 ? `${Math.round(secsAgo / 60)}m` : `${secsAgo}s`;
    return {
      time: label,
      pps: Math.round(point.pps * 10) / 10,
    };
  });

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id="ppsGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#1890ff" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#1890ff" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="time"
          tick={{ fill: '#6b6b8a', fontSize: 10 }}
          axisLine={{ stroke: '#2d2d52' }}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fill: '#6b6b8a', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          width={40}
        />
        <Tooltip
          contentStyle={{
            background: '#1a1a2e',
            border: '1px solid #2d2d52',
            borderRadius: 6,
            color: '#fff',
          }}
          formatter={(value: number) => [`${value} pkt/s`, 'Rate']}
        />
        <Area
          type="monotone"
          dataKey="pps"
          stroke="#1890ff"
          fillOpacity={1}
          fill="url(#ppsGradient)"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default PacketRateSparkline;
