/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Downloads API Client
 * Manages downloadable resources
 */

import apiClient from './client';

const DOWNLOADS_PREFIX = '/api/v1/downloads';

export interface DownloadableFile {
  name: string;
  filename: string;
  description: string;
  size_bytes: number;
  size_human: string;
  category: string;
}

export interface DownloadsListResponse {
  files: DownloadableFile[];
}

export const downloadsApi = {
  /**
   * List all available downloads
   */
  async list(): Promise<DownloadsListResponse> {
    const response = await apiClient.get<DownloadsListResponse>(DOWNLOADS_PREFIX);
    return response.data;
  },

  /**
   * Get the download URL for a file
   */
  getDownloadUrl(filename: string): string {
    // Get the base URL from the API client config
    const baseUrl = apiClient.defaults.baseURL || '';
    return `${baseUrl}${DOWNLOADS_PREFIX}/${filename}`;
  },

  /**
   * Trigger a file download
   */
  async downloadFile(filename: string): Promise<void> {
    const url = this.getDownloadUrl(filename);

    // Create a temporary anchor element to trigger download
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },
};
