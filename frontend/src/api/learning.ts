/**
 * Learning API client for PCAP uploads and patterns
 */

import { apiClient } from './client';

// Types for learning API responses
export interface PcapUploadResponse {
  id: string;
  filename: string;
  status: string;
  message: string;
}

export interface PcapCapture {
  id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message: string | null;
  packet_count: number | null;
  flow_count: number | null;
  capture_duration_ms: number | null;
  protocol_stats: {
    packet_counts?: Record<string, number>;
    flow_counts?: Record<string, number>;
  } | Record<string, number> | null;
  devices_detected: Record<string, unknown> | null;
  description: string | null;
  tags: string[] | null;
  source_environment: string | null;
  industry_vertical: string | null;
  created_at: string;
  processed_at: string | null;
}

export interface PcapListResponse {
  captures: PcapCapture[];
  total: number;
  page: number;
  page_size: number;
}

export interface LearnedPattern {
  id: string;
  name: string;
  pattern_type: string;
  protocol: string;
  source_ip: string | null;
  destination_ip: string | null;
  distribution_type: string | null;
  sample_count: number;
  min_value: number | null;
  max_value: number | null;
  mean_value: number | null;
  std_dev: number | null;
  fit_score: number | null;
  confidence: number;
  is_active: boolean;
  created_at: string;
}

export interface PatternListResponse {
  patterns: LearnedPattern[];
  total: number;
  page: number;
  page_size: number;
}

export interface PatternDetail extends LearnedPattern {
  source_port: number | null;
  destination_port: number | null;
  timing_params: Record<string, unknown> | null;
  payload_patterns: Record<string, unknown> | null;
  sequence_patterns: Record<string, unknown> | null;
  error_patterns: Record<string, unknown> | null;
  pattern_data: Record<string, unknown> | null;
  updated_at: string;
}

export interface LearningStats {
  uploaded_pcaps: number;
  learned_patterns: number;
  active_patterns: number;
  protocols_covered: number;
  protocol_patterns: number;
  device_fingerprints: number;
  learned_sequences: number;
}

// Enhanced pattern types
export interface ProtocolPattern {
  id: string;
  pcap_capture_id: string | null;
  protocol: string;
  function_codes: Record<string, unknown> | null;
  address_patterns: Record<string, unknown> | null;
  payload_structures: Record<string, unknown> | null;
  request_response_pairs: unknown[] | null;
  unit_id_distribution: Record<string, unknown> | null;
  exception_patterns: Record<string, unknown> | null;
  device_identities: unknown[] | null;
  protocol_metadata: Record<string, unknown> | null;
  sample_count: number;
  created_at: string;
}

export interface ProtocolPatternListResponse {
  patterns: ProtocolPattern[];
  total: number;
  page: number;
  page_size: number;
}

export interface DeviceFingerprint {
  id: string;
  pcap_capture_id: string | null;
  ip_address: string;
  mac_address: string | null;
  mac_oui: string | null;
  inferred_vendor: string | null;
  tcp_signature: Record<string, unknown> | null;
  response_timings: Record<string, unknown> | null;
  protocol_identities: Record<string, unknown> | null;
  role: string;
  communication_partners: string[] | null;
  active_protocols: string[] | null;
  created_at: string;
}

export interface DeviceFingerprintListResponse {
  fingerprints: DeviceFingerprint[];
  total: number;
  page: number;
  page_size: number;
}

export interface LearnedSequence {
  id: string;
  pcap_capture_id: string | null;
  name: string;
  sequence_type: string;
  protocol: string;
  initiator_ip: string | null;
  responder_ip: string | null;
  steps: Record<string, unknown> | null;
  step_count: number;
  average_duration_ms: number | null;
  timing_variance: number | null;
  inter_step_timings: Record<string, unknown> | null;
  repetition_interval_ms: number | null;
  repetition_jitter_ms: number | null;
  occurrence_count: number;
  confidence: number;
  created_at: string;
}

export interface SequenceListResponse {
  sequences: LearnedSequence[];
  total: number;
  page: number;
  page_size: number;
}

// Pattern service types
export interface TimingModel {
  protocol: string;
  source_pattern_id: string | null;
  timing: Record<string, unknown> | null;
  confidence: number;
}

export interface FunctionCodeDistribution {
  protocol: string;
  source_pattern_id: string | null;
  function_codes: Record<string, unknown> | null;
  sample_count: number;
  confidence: number;
}

export interface AddressPatterns {
  protocol: string;
  source_pattern_id: string | null;
  address_patterns: Record<string, unknown> | null;
  sample_count: number;
  confidence: number;
}

export interface TcpSignatureModel {
  protocol: string | null;
  role: string | null;
  signatures: Array<{
    source_ip: string;
    signature: Record<string, unknown>;
    vendor: string | null;
  }>;
  count: number;
}

export interface ResponseTimingModel {
  protocol: string;
  role: string;
  aggregate: {
    mean_ms: number;
    min_ms: number;
    max_ms: number;
  };
  individual_timings: unknown[];
  device_count: number;
}

export interface StartupSequence {
  protocol: string;
  sequence_id: string;
  name: string;
  steps: Record<string, unknown> | null;
  step_count: number;
  average_duration_ms: number | null;
  confidence: number;
}

export interface PollCyclePattern {
  protocol: string;
  sequence_id: string;
  name: string;
  steps: Record<string, unknown> | null;
  step_count: number;
  repetition_interval_ms: number | null;
  repetition_jitter_ms: number | null;
  confidence: number;
}

export interface PatternSuggestion {
  device_type: string;
  protocol: string;
  expected_role: string;
  suggestions: {
    protocol_patterns: Array<{
      id: string;
      sample_count: number;
      confidence: number;
      has_function_codes: boolean;
      has_address_patterns: boolean;
      has_timing: boolean;
    }>;
    fingerprints: Array<{
      id: string;
      ip_address: string;
      vendor: string | null;
      role: string;
      has_tcp_signature: boolean;
      has_response_timings: boolean;
      confidence: number;
    }>;
    sequences: Array<{
      id: string;
      name: string;
      sequence_type: string;
      step_count: number;
      confidence: number;
    }>;
  };
}

export interface PatternStats {
  protocol_patterns: Record<string, { count: number; avg_confidence: number }>;
  device_fingerprints: Record<string, number>;
  sequences: Record<string, Record<string, number>>;
}

// API functions

export async function getLearningStats(): Promise<LearningStats> {
  const response = await apiClient.get<LearningStats>('/api/v1/learning/stats');
  return response.data;
}
export async function uploadPcap(
  file: File,
  options?: {
    description?: string;
    source_environment?: string;
    industry_vertical?: string;
  }
): Promise<PcapUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const params = new URLSearchParams();
  if (options?.description) params.append('description', options.description);
  if (options?.source_environment) params.append('source_environment', options.source_environment);
  if (options?.industry_vertical) params.append('industry_vertical', options.industry_vertical);

  const queryString = params.toString() ? `?${params.toString()}` : '';
  const response = await apiClient.post<PcapUploadResponse>(
    `/api/v1/learning/pcap/upload${queryString}`,
    formData,
    {
      headers: {
        // Let axios set Content-Type automatically with proper boundary for multipart/form-data
        'Content-Type': undefined,
      },
    }
  );
  return response.data;
}

export async function listPcapCaptures(options?: {
  page?: number;
  page_size?: number;
  status?: string;
}): Promise<PcapListResponse> {
  const response = await apiClient.get<PcapListResponse>('/api/v1/learning/pcap', {
    params: options,
  });
  return response.data;
}

export async function getPcapCapture(captureId: string): Promise<PcapCapture> {
  const response = await apiClient.get<PcapCapture>(
    `/api/v1/learning/pcap/${encodeURIComponent(captureId)}`
  );
  return response.data;
}

export async function deletePcapCapture(captureId: string): Promise<{ message: string }> {
  const response = await apiClient.delete<{ message: string }>(
    `/api/v1/learning/pcap/${encodeURIComponent(captureId)}`
  );
  return response.data;
}

export async function retryPcapProcessing(captureId: string): Promise<PcapUploadResponse> {
  const response = await apiClient.post<PcapUploadResponse>(
    `/api/v1/learning/pcap/${encodeURIComponent(captureId)}/retry`
  );
  return response.data;
}

export async function listPatterns(options?: {
  page?: number;
  page_size?: number;
  protocol?: string;
  pattern_type?: string;
  active_only?: boolean;
}): Promise<PatternListResponse> {
  const response = await apiClient.get<PatternListResponse>('/api/v1/learning/patterns', {
    params: options,
  });
  return response.data;
}

export async function getPattern(patternId: string): Promise<PatternDetail> {
  const response = await apiClient.get<PatternDetail>(
    `/api/v1/learning/patterns/${encodeURIComponent(patternId)}`
  );
  return response.data;
}

export async function togglePattern(patternId: string): Promise<{ id: string; is_active: boolean }> {
  const response = await apiClient.patch<{ id: string; is_active: boolean }>(
    `/api/v1/learning/patterns/${encodeURIComponent(patternId)}/toggle`
  );
  return response.data;
}

// Enhanced pattern endpoints

export async function listProtocolPatterns(options?: {
  page?: number;
  page_size?: number;
  protocol?: string;
  pcap_capture_id?: string;
}): Promise<ProtocolPatternListResponse> {
  const response = await apiClient.get<ProtocolPatternListResponse>('/api/v1/learning/protocol-patterns', {
    params: options,
  });
  return response.data;
}

export async function getProtocolPattern(patternId: string): Promise<ProtocolPattern> {
  const response = await apiClient.get<ProtocolPattern>(
    `/api/v1/learning/protocol-patterns/${encodeURIComponent(patternId)}`
  );
  return response.data;
}

export async function listDeviceFingerprints(options?: {
  page?: number;
  page_size?: number;
  vendor?: string;
  role?: string;
  protocol?: string;
  pcap_capture_id?: string;
}): Promise<DeviceFingerprintListResponse> {
  const response = await apiClient.get<DeviceFingerprintListResponse>('/api/v1/learning/device-fingerprints', {
    params: options,
  });
  return response.data;
}

export async function getDeviceFingerprint(fingerprintId: string): Promise<DeviceFingerprint> {
  const response = await apiClient.get<DeviceFingerprint>(
    `/api/v1/learning/device-fingerprints/${encodeURIComponent(fingerprintId)}`
  );
  return response.data;
}

export async function listSequences(options?: {
  page?: number;
  page_size?: number;
  sequence_type?: string;
  protocol?: string;
  pcap_capture_id?: string;
}): Promise<SequenceListResponse> {
  const response = await apiClient.get<SequenceListResponse>('/api/v1/learning/sequences', {
    params: options,
  });
  return response.data;
}

export async function getSequence(sequenceId: string): Promise<LearnedSequence> {
  const response = await apiClient.get<LearnedSequence>(
    `/api/v1/learning/sequences/${encodeURIComponent(sequenceId)}`
  );
  return response.data;
}

// Pattern service endpoints

export async function getTimingModel(protocol: string): Promise<TimingModel> {
  const response = await apiClient.get<TimingModel>(
    `/api/v1/learning/patterns/timing-model/${encodeURIComponent(protocol)}`
  );
  return response.data;
}

export async function getFunctionCodes(protocol: string): Promise<FunctionCodeDistribution> {
  const response = await apiClient.get<FunctionCodeDistribution>(
    `/api/v1/learning/patterns/function-codes/${encodeURIComponent(protocol)}`
  );
  return response.data;
}

export async function getAddressPatterns(protocol: string): Promise<AddressPatterns> {
  const response = await apiClient.get<AddressPatterns>(
    `/api/v1/learning/patterns/address-patterns/${encodeURIComponent(protocol)}`
  );
  return response.data;
}

export async function getTcpSignatures(options?: {
  protocol?: string;
  role?: string;
}): Promise<TcpSignatureModel> {
  const response = await apiClient.get<TcpSignatureModel>('/api/v1/learning/patterns/tcp-signatures', {
    params: options,
  });
  return response.data;
}

export async function getResponseTiming(protocol: string, role?: string): Promise<ResponseTimingModel> {
  const response = await apiClient.get<ResponseTimingModel>(
    `/api/v1/learning/patterns/response-timing/${encodeURIComponent(protocol)}`,
    { params: { role } }
  );
  return response.data;
}

export async function getStartupSequence(protocol: string): Promise<StartupSequence> {
  const response = await apiClient.get<StartupSequence>(
    `/api/v1/learning/patterns/startup-sequence/${encodeURIComponent(protocol)}`
  );
  return response.data;
}

export async function getPollCycle(protocol: string): Promise<PollCyclePattern> {
  const response = await apiClient.get<PollCyclePattern>(
    `/api/v1/learning/patterns/poll-cycle/${encodeURIComponent(protocol)}`
  );
  return response.data;
}

export async function suggestPatterns(deviceType: string, protocol: string): Promise<PatternSuggestion> {
  const response = await apiClient.get<PatternSuggestion>('/api/v1/learning/patterns/suggest', {
    params: { device_type: deviceType, protocol },
  });
  return response.data;
}

export async function getPatternStats(): Promise<PatternStats> {
  const response = await apiClient.get<PatternStats>('/api/v1/learning/patterns/stats');
  return response.data;
}
