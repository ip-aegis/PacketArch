/**
 * AI Assistant API client
 */

import apiClient from './client';

export interface AISession {
  session_id: string;
  created_at: string;
  scenario_id?: string;
  messages: Array<{ role: 'user' | 'assistant'; content: string }>;
}

export interface AISessionCreateRequest {
  scenario_id: string;
}

export interface AIChatRequest {
  session_id: string;
  scenario_id: string;
  message: string;
}

export interface AIChatResponse {
  response: string;
  tool_calls: ToolCall[];
  pending_actions: string[];
}

export interface ToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
}

export interface AITool {
  name: string;
  description: string;
  category: string;
}

// Streaming event types
export type AIStreamEventType = 'start' | 'thinking' | 'tool_start' | 'tool_complete' | 'text' | 'done' | 'error';

export interface AIStreamEventBase {
  type: AIStreamEventType;
}

export interface AIStreamStartEvent extends AIStreamEventBase {
  type: 'start';
  message: string;
}

export interface AIStreamThinkingEvent extends AIStreamEventBase {
  type: 'thinking';
  message: string;
  iteration?: number;
}

export interface AIStreamToolStartEvent extends AIStreamEventBase {
  type: 'tool_start';
  name: string;
  input: Record<string, unknown>;
}

export interface AIStreamToolCompleteEvent extends AIStreamEventBase {
  type: 'tool_complete';
  name: string;
  success: boolean;
  result_preview?: string;
  error?: string;
}

export interface AIStreamTextEvent extends AIStreamEventBase {
  type: 'text';
  content: string;
}

export interface AIStreamDoneEvent extends AIStreamEventBase {
  type: 'done';
  response: string;
  tool_calls: ToolCall[];
  tool_count: number;
}

export interface AIStreamErrorEvent extends AIStreamEventBase {
  type: 'error';
  message: string;
}

export type AIStreamEvent =
  | AIStreamStartEvent
  | AIStreamThinkingEvent
  | AIStreamToolStartEvent
  | AIStreamToolCompleteEvent
  | AIStreamTextEvent
  | AIStreamDoneEvent
  | AIStreamErrorEvent;

export interface AIStreamCallbacks {
  onStart?: (event: AIStreamStartEvent) => void;
  onThinking?: (event: AIStreamThinkingEvent) => void;
  onToolStart?: (event: AIStreamToolStartEvent) => void;
  onToolComplete?: (event: AIStreamToolCompleteEvent) => void;
  onText?: (event: AIStreamTextEvent) => void;
  onDone?: (event: AIStreamDoneEvent) => void;
  onError?: (event: AIStreamErrorEvent) => void;
}

export const aiApi = {
  /**
   * Create or resume an AI session for a scenario.
   * If a session already exists for this scenario, returns it with conversation history.
   */
  createSession: async (request: AISessionCreateRequest): Promise<AISession> => {
    const response = await apiClient.post<AISession>('/api/v1/ai/sessions', request);
    return response.data;
  },

  /**
   * Get existing session for a scenario (if any)
   */
  getSessionForScenario: async (scenarioId: string): Promise<AISession | null> => {
    try {
      const response = await apiClient.get<AISession | null>(`/api/v1/ai/sessions/scenario/${scenarioId}`);
      return response.data;
    } catch {
      return null;
    }
  },

  /**
   * Clear conversation for a scenario (delete session)
   */
  clearConversation: async (scenarioId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/ai/sessions/scenario/${scenarioId}`);
  },

  /**
   * End an AI session (legacy - for backwards compatibility)
   */
  endSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/ai/sessions/${sessionId}`);
  },

  /**
   * Send a message to the AI
   */
  sendMessage: async (request: AIChatRequest): Promise<AIChatResponse> => {
    const response = await apiClient.post<AIChatResponse>('/api/v1/ai/chat', request);
    return response.data;
  },

  /**
   * Accept a proposed action
   */
  acceptAction: async (actionId: string): Promise<{ success: boolean; action_id: string }> => {
    const response = await apiClient.post<{ success: boolean; action_id: string }>(
      `/api/v1/ai/actions/${actionId}/accept`
    );
    return response.data;
  },

  /**
   * Reject a proposed action
   */
  rejectAction: async (actionId: string): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>(
      `/api/v1/ai/actions/${actionId}/reject`
    );
    return response.data;
  },

  /**
   * Get available AI tools
   */
  getTools: async (): Promise<AITool[]> => {
    const response = await apiClient.get<AITool[]>('/api/v1/ai/tools');
    return response.data;
  },

  /**
   * Send a message to the AI with streaming response
   * Uses Server-Sent Events to receive real-time updates
   */
  sendMessageStream: async (
    request: AIChatRequest,
    callbacks: AIStreamCallbacks,
    abortSignal?: AbortSignal
  ): Promise<void> => {
    // Get auth token from localStorage
    const token = localStorage.getItem('auth_token');

    // Build URL with API base
    const baseUrl = apiClient.defaults.baseURL || '';
    const url = `${baseUrl}/api/v1/ai/chat/stream`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
      },
      body: JSON.stringify(request),
      signal: abortSignal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Stream request failed: ${response.status} ${errorText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE events (data: {...}\n\n)
        const events = buffer.split('\n\n');
        buffer = events.pop() || ''; // Keep incomplete event in buffer

        for (const eventStr of events) {
          if (!eventStr.trim()) continue;

          // Parse SSE data
          const dataMatch = eventStr.match(/^data: (.+)$/m);
          if (!dataMatch) continue;

          try {
            const event = JSON.parse(dataMatch[1]) as AIStreamEvent;

            // Dispatch to appropriate callback
            switch (event.type) {
              case 'start':
                callbacks.onStart?.(event);
                break;
              case 'thinking':
                callbacks.onThinking?.(event);
                break;
              case 'tool_start':
                callbacks.onToolStart?.(event);
                break;
              case 'tool_complete':
                callbacks.onToolComplete?.(event);
                break;
              case 'text':
                callbacks.onText?.(event);
                break;
              case 'done':
                callbacks.onDone?.(event);
                break;
              case 'error':
                callbacks.onError?.(event);
                break;
            }
          } catch (parseError) {
            console.warn('Failed to parse SSE event:', eventStr, parseError);
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },
};

export default aiApi;
