/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AI Assistant state management with Zustand
 * Supports both standard and streaming API modes
 */

import { create } from 'zustand';
import { aiApi } from '../api/ai';
import { scenariosApi } from '../api/scenarios';
import { useScenarioStore } from './scenarioStore';
import type {
  AIStreamStartEvent,
  AIStreamThinkingEvent,
  AIStreamToolStartEvent,
  AIStreamToolCompleteEvent,
  AIStreamTextEvent,
  AIStreamDoneEvent,
  AIStreamErrorEvent,
} from '../api/ai';

// Helper to refresh scenario after AI modifications
const refreshScenarioCanvas = async (scenarioId: string) => {
  try {
    // Add small delay to ensure database commit is complete
    await new Promise(resolve => setTimeout(resolve, 200));

    const scenario = await scenariosApi.get(scenarioId);
    const definition = scenario.definition as {
      devices?: Record<string, unknown>;
      flows?: Record<string, unknown>;
      zones?: Record<string, unknown>;
      phases?: unknown[];
    };

    const deviceCount = Object.keys(definition?.devices || {}).length;
    const flowCount = Object.keys(definition?.flows || {}).length;

    console.log(`Refreshing scenario canvas: ${deviceCount} devices, ${flowCount} flows`);

    useScenarioStore.getState().loadScenario({
      id: scenario.id,
      name: scenario.name,
      description: scenario.description || '',
      vertical: scenario.vertical || undefined,
      totalDurationMs: scenario.total_duration_ms,
      devices: (definition?.devices || {}) as Record<string, import('../types').ScenarioDevice>,
      flows: (definition?.flows || {}) as Record<string, import('../types').ScenarioFlow>,
      zones: (definition?.zones || {}) as Record<string, import('../types').ScenarioZone>,
      phases: (definition?.phases || []) as import('../types').Phase[],
      addressingConfig: scenario.addressing_config as {
        ip_range?: string;
        range_index?: number;
        auto_assign_enabled?: boolean;
      } | null,
    });
    // Studio v2 keeps its own document — refresh it too when it has the
    // same scenario open (the /studio2 route doesn't use scenarioStore).
    try {
      const { useDocumentStore } = await import('../studio2/document/documentStore');
      const { parseScenario } = await import('../studio2/document/codec');
      if (useDocumentStore.getState().doc?.meta.id === scenarioId) {
        useDocumentStore.getState().loadDocument(parseScenario(scenario));
      }
    } catch (e) {
      console.warn('Studio v2 document refresh skipped:', e);
    }
    console.log('Scenario canvas refreshed after AI modifications');
  } catch (error) {
    console.error('Failed to refresh scenario after AI modifications:', error);
  }
};

// Helper to extract new scenario ID from tool results
const extractNewScenarioId = (toolCalls: Array<{ name: string; result?: string }>): string | null => {
  for (const call of toolCalls) {
    if (call.name === 'generate_scenario_from_nl' && call.result) {
      try {
        const result = JSON.parse(call.result);
        if (result.success && result.scenario_id) {
          return result.scenario_id;
        }
      } catch {
        // Ignore parse errors
      }
    }
  }
  return null;
};

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
  timestamp: string;
  isStreaming?: boolean;
}

export interface ToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
  result?: string;
  success?: boolean;
  executionTime?: number;
}

export interface PendingAction {
  id: string;
  description: string;
  action: string;
  params: Record<string, unknown>;
}

export interface ToolProgress {
  name: string;
  status: 'running' | 'complete' | 'error';
  result_preview?: string;
  error?: string;
}

interface AIAssistantState {
  isOpen: boolean;
  isConnected: boolean;
  isProcessing: boolean;
  currentScenarioId: string | null;
  sessionId: string | null;
  messages: Message[];
  pendingActions: PendingAction[];

  // Streaming state
  useStreaming: boolean;
  streamingContent: string;
  currentToolExecution: string | null;
  toolProgress: ToolProgress[];
  thinkingMessage: string | null;
  abortController: AbortController | null;

  // Actions
  openPanel: (scenarioId: string) => Promise<void>;
  closePanel: () => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  sendMessageStream: (message: string) => Promise<void>;
  cancelStream: () => void;
  acceptAction: (actionId: string) => Promise<void>;
  rejectAction: (actionId: string) => Promise<void>;
  clearConversation: () => Promise<void>;
  addMessage: (message: Message) => void;
  setProcessing: (processing: boolean) => void;
  setSessionId: (sessionId: string | null) => void;
  setUseStreaming: (useStreaming: boolean) => void;
}

export const useAIAssistantStore = create<AIAssistantState>((set, get) => ({
  isOpen: false,
  isConnected: false,
  isProcessing: false,
  currentScenarioId: null,
  sessionId: null,
  messages: [],
  pendingActions: [],

  // Streaming state
  useStreaming: true, // Enable streaming by default
  streamingContent: '',
  currentToolExecution: null,
  toolProgress: [],
  thinkingMessage: null,
  abortController: null,

  openPanel: async (scenarioId: string) => {
    // Get or create AI session for this scenario (persists across panel opens)
    try {
      const session = await aiApi.createSession({ scenario_id: scenarioId });

      // Convert session messages to our Message format
      const existingMessages: Message[] = (session.messages || []).map((msg, index) => ({
        id: `msg_${session.created_at}_${index}`,
        role: msg.role,
        content: msg.content,
        timestamp: session.created_at,
      }));

      set({
        isOpen: true,
        currentScenarioId: scenarioId,
        sessionId: session.session_id,
        isConnected: true,
        // Load existing conversation from session
        messages: existingMessages,
        pendingActions: [],
        streamingContent: '',
        toolProgress: [],
        thinkingMessage: null,
      });

      if (existingMessages.length > 0) {
        console.log(`Resumed AI session with ${existingMessages.length} messages`);
      }
    } catch (error) {
      console.error('Failed to create/resume AI session:', error);
      set({
        isOpen: true,
        currentScenarioId: scenarioId,
        isConnected: false,
        // Clear previous conversation on error
        messages: [],
        pendingActions: [],
      });
    }
  },

  closePanel: async () => {
    const state = get();

    // Cancel any active stream
    if (state.abortController) {
      state.abortController.abort();
    }

    // NOTE: We do NOT delete the session on close - it persists for this scenario.
    // User can clear conversation explicitly via the "Clear conversation" button.

    set({
      isOpen: false,
      // Keep scenario/session IDs for potential reopen
      currentScenarioId: null,
      sessionId: null,
      // Clear local state but session persists in Redis
      messages: [],
      pendingActions: [],
      isConnected: false,
      // Reset streaming state
      streamingContent: '',
      currentToolExecution: null,
      toolProgress: [],
      thinkingMessage: null,
      abortController: null,
    });
  },

  sendMessage: async (message: string) => {
    const state = get();

    if (!state.currentScenarioId || !state.sessionId) {
      console.error('No scenario or session');
      return;
    }

    // Add user message
    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    set({ messages: [...state.messages, userMessage], isProcessing: true });

    try {
      const response = await aiApi.sendMessage({
        session_id: state.sessionId,
        scenario_id: state.currentScenarioId,
        message,
      });

      const assistantMessage: Message = {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: response.response,
        toolCalls: response.tool_calls,
        timestamp: new Date().toISOString(),
      };

      set(state => ({
        messages: [...state.messages, assistantMessage],
        isProcessing: false,
      }));

      // Always refresh scenario canvas after AI response completes
      if (state.currentScenarioId) {
        // Check if a new scenario was created (generate_scenario_from_nl)
        const newScenarioId = response.tool_calls ? extractNewScenarioId(response.tool_calls) : null;

        if (newScenarioId && newScenarioId !== state.currentScenarioId) {
          // New scenario created - refresh that one and navigate to it
          console.log(`New scenario created: ${newScenarioId}`);
          await refreshScenarioCanvas(newScenarioId);

          // Update current scenario ID to the new one
          set({ currentScenarioId: newScenarioId });

          // Navigate to the new scenario
          window.location.href = `/studio?scenario=${newScenarioId}`;
        } else {
          // Same scenario - just refresh to get latest data
          await refreshScenarioCanvas(state.currentScenarioId);
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);

      // Add error message
      const errorMessage: Message = {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request.',
        timestamp: new Date().toISOString(),
      };

      set(state => ({
        messages: [...state.messages, errorMessage],
        isProcessing: false,
      }));
    }
  },

  sendMessageStream: async (message: string) => {
    const state = get();

    if (!state.currentScenarioId || !state.sessionId) {
      console.error('No scenario or session');
      return;
    }

    // Create abort controller for cancellation
    const abortController = new AbortController();

    // Add user message
    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    // Create a placeholder for the assistant message that will be streamed
    const assistantMessageId = `msg_${Date.now() + 1}`;

    set({
      messages: [...state.messages, userMessage],
      isProcessing: true,
      streamingContent: '',
      toolProgress: [],
      currentToolExecution: null,
      thinkingMessage: 'Processing your request...',
      abortController,
    });

    try {
      await aiApi.sendMessageStream(
        {
          session_id: state.sessionId,
          scenario_id: state.currentScenarioId,
          message,
        },
        {
          onStart: (event: AIStreamStartEvent) => {
            set({ thinkingMessage: event.message });
          },

          onThinking: (event: AIStreamThinkingEvent) => {
            set({ thinkingMessage: event.message });
          },

          onToolStart: (event: AIStreamToolStartEvent) => {
            set(state => ({
              currentToolExecution: event.name,
              toolProgress: [
                ...state.toolProgress,
                { name: event.name, status: 'running' },
              ],
            }));
          },

          onToolComplete: (event: AIStreamToolCompleteEvent) => {
            set(state => ({
              currentToolExecution: null,
              toolProgress: state.toolProgress.map(tp =>
                tp.name === event.name
                  ? {
                      ...tp,
                      status: event.success ? 'complete' : 'error',
                      result_preview: event.result_preview,
                      error: event.error,
                    }
                  : tp
              ),
            }));
          },

          onText: (event: AIStreamTextEvent) => {
            set(state => ({
              streamingContent: state.streamingContent + event.content,
              thinkingMessage: null,
            }));
          },

          onDone: async (event: AIStreamDoneEvent) => {
            // Finalize the assistant message
            const assistantMessage: Message = {
              id: assistantMessageId,
              role: 'assistant',
              content: event.response,
              toolCalls: event.tool_calls,
              timestamp: new Date().toISOString(),
            };

            set(currentState => ({
              messages: [...currentState.messages, assistantMessage],
              isProcessing: false,
              streamingContent: '',
              thinkingMessage: null,
              abortController: null,
            }));

            // Always refresh scenario canvas after AI response completes
            if (state.currentScenarioId) {
              // Check if a new scenario was created (generate_scenario_from_nl)
              const newScenarioId = event.tool_calls ? extractNewScenarioId(event.tool_calls) : null;

              if (newScenarioId && newScenarioId !== state.currentScenarioId) {
                // New scenario created - refresh that one and notify user
                console.log(`New scenario created: ${newScenarioId}`);
                await refreshScenarioCanvas(newScenarioId);

                // Update current scenario ID to the new one
                set({ currentScenarioId: newScenarioId });

                // Navigate to the new scenario (user needs to see it)
                window.location.href = `/studio?scenario=${newScenarioId}`;
              } else {
                // Same scenario - just refresh to get latest data
                await refreshScenarioCanvas(state.currentScenarioId);
              }
            }
          },

          onError: (event: AIStreamErrorEvent) => {
            const errorMessage: Message = {
              id: assistantMessageId,
              role: 'assistant',
              content: `Error: ${event.message}`,
              timestamp: new Date().toISOString(),
            };

            set(state => ({
              messages: [...state.messages, errorMessage],
              isProcessing: false,
              streamingContent: '',
              thinkingMessage: null,
              abortController: null,
            }));
          },
        },
        abortController.signal
      );
    } catch (error) {
      // Handle abort or other errors
      if ((error as Error).name === 'AbortError') {
        console.log('Stream was cancelled');
      } else {
        console.error('Error in streaming message:', error);
        const errorMessage: Message = {
          id: `msg_${Date.now()}`,
          role: 'assistant',
          content: 'Sorry, I encountered an error processing your request.',
          timestamp: new Date().toISOString(),
        };

        set(state => ({
          messages: [...state.messages, errorMessage],
        }));
      }

      set({
        isProcessing: false,
        streamingContent: '',
        thinkingMessage: null,
        abortController: null,
      });
    }
  },

  cancelStream: () => {
    const state = get();
    if (state.abortController) {
      state.abortController.abort();
      set({
        isProcessing: false,
        streamingContent: '',
        thinkingMessage: null,
        abortController: null,
      });
    }
  },

  acceptAction: async (actionId: string) => {
    const state = get();
    const action = state.pendingActions.find(a => a.id === actionId);

    if (!action) {
      console.error('Action not found:', actionId);
      return;
    }

    try {
      await aiApi.acceptAction(actionId);

      // Remove from pending actions
      set({
        pendingActions: state.pendingActions.filter(a => a.id !== actionId),
      });

      // Add confirmation message
      const confirmMessage: Message = {
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: `Action "${action.description}" has been applied successfully.`,
        timestamp: new Date().toISOString(),
      };

      set(state => ({
        messages: [...state.messages, confirmMessage],
      }));
    } catch (error) {
      console.error('Error accepting action:', error);
    }
  },

  rejectAction: async (actionId: string) => {
    const state = get();

    try {
      await aiApi.rejectAction(actionId);

      // Remove from pending actions
      set({
        pendingActions: state.pendingActions.filter(a => a.id !== actionId),
      });
    } catch (error) {
      console.error('Error rejecting action:', error);
    }
  },

  clearConversation: async () => {
    const state = get();

    // Clear conversation in backend (Redis)
    if (state.currentScenarioId) {
      try {
        await aiApi.clearConversation(state.currentScenarioId);
        console.log('Conversation cleared for scenario:', state.currentScenarioId);
      } catch (error) {
        console.error('Failed to clear conversation:', error);
      }

      // Create a fresh session for the same scenario
      try {
        const session = await aiApi.createSession({ scenario_id: state.currentScenarioId });
        set({
          sessionId: session.session_id,
          messages: [],
          pendingActions: [],
        });
      } catch (error) {
        console.error('Failed to create new session after clear:', error);
        set({
          messages: [],
          pendingActions: [],
        });
      }
    } else {
      // Fallback: just clear local state
      set({
        messages: [],
        pendingActions: [],
      });
    }
  },

  addMessage: (message: Message) => {
    set(state => ({
      messages: [...state.messages, message],
    }));
  },

  setProcessing: (processing: boolean) => {
    set({ isProcessing: processing });
  },

  setSessionId: (sessionId: string | null) => {
    set({ sessionId, isConnected: sessionId !== null });
  },

  setUseStreaming: (useStreaming: boolean) => {
    set({ useStreaming });
  },
}));

export default useAIAssistantStore;
