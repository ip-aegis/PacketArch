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
    const scenario = await scenariosApi.get(scenarioId);
    const definition = scenario.definition as {
      devices?: Record<string, unknown>;
      flows?: Record<string, unknown>;
      zones?: Record<string, unknown>;
      phases?: unknown[];
    };

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
    console.log('Scenario canvas refreshed after AI modifications');
  } catch (error) {
    console.error('Failed to refresh scenario after AI modifications:', error);
  }
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
  clearConversation: () => void;
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
    // Create AI session - always start fresh
    try {
      const session = await aiApi.createSession();
      set({
        isOpen: true,
        currentScenarioId: scenarioId,
        sessionId: session.session_id,
        isConnected: true,
        // Clear previous conversation
        messages: [],
        pendingActions: [],
        streamingContent: '',
        toolProgress: [],
        thinkingMessage: null,
      });
    } catch (error) {
      console.error('Failed to create AI session:', error);
      set({
        isOpen: true,
        currentScenarioId: scenarioId,
        isConnected: false,
        // Clear previous conversation even on error
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

    // End session if exists
    if (state.sessionId) {
      try {
        await aiApi.endSession(state.sessionId);
      } catch (error) {
        console.error('Failed to end AI session:', error);
      }
    }

    set({
      isOpen: false,
      currentScenarioId: null,
      sessionId: null,
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

      // Refresh scenario canvas if tools were executed
      if (response.tool_calls && response.tool_calls.length > 0) {
        await refreshScenarioCanvas(state.currentScenarioId);
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
      let finalToolCalls: ToolCall[] = [];

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
            finalToolCalls = event.tool_calls;

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

            // Refresh scenario canvas if tools were executed
            if (event.tool_calls && event.tool_calls.length > 0 && state.currentScenarioId) {
              await refreshScenarioCanvas(state.currentScenarioId);
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

  clearConversation: () => {
    set({
      messages: [],
      pendingActions: [],
    });
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
