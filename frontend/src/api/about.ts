/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Product metadata: version, build info, ownership, license.
 * Unauthenticated — safe to call from the login page footer.
 */

import apiClient from './client';

export interface OwnerInfo {
  name: string;
  email: string;
  copyright: string;
}

export interface LicenseInfo {
  id: string;
  name: string;
  url: string;
}

export interface AcknowledgmentInfo {
  document: string;
  version: string;
  title: string;
  body: string;
}

export interface Features {
  ai_enabled: boolean;
  live_traffic_enabled: boolean;
  multi_sensor_topology_enabled: boolean;
  mimic_enabled: boolean;
}

export interface AboutResponse {
  name: string;
  version: string;
  build_commit: string;
  build_date: string;
  owner: OwnerInfo;
  license: LicenseInfo;
  acknowledgment: AcknowledgmentInfo;
  features: Features;
}

const ABOUT_PREFIX = '/api/v1/about';

export const aboutApi = {
  async get(): Promise<AboutResponse> {
    const response = await apiClient.get<AboutResponse>(ABOUT_PREFIX);
    return response.data;
  },
};

export default aboutApi;
