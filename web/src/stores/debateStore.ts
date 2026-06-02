import { create } from 'zustand';
import type { DebateSession, Message, DebateEvent } from '../types/debate';
import * as api from '../api/client';

interface DebateState {
  // Current debate
  session: DebateSession | null;
  messages: Message[];
  currentDimension: string | null;
  isStreaming: boolean;
  streamingRole: string | null;
  streamingContent: string;

  // History
  history: DebateSession[];

  // Actions
  healthCheck: () => Promise<Record<string, unknown>>;
  createDebate: (topic: string, mode: string) => Promise<string>;
  loadDebate: (id: string) => Promise<void>;
  loadHistory: () => Promise<void>;
  handleEvent: (event: DebateEvent) => void;
  pause: () => Promise<void>;
  resume: () => Promise<void>;
  stop: () => Promise<void>;
  skipRound: () => Promise<void>;
  reset: () => void;
}

export const useDebateStore = create<DebateState>((set, get) => ({
  session: null,
  messages: [],
  currentDimension: null,
  isStreaming: false,
  streamingRole: null,
  streamingContent: '',

  history: [],

  healthCheck: async () => {
    const r = await fetch('/api/models/health');
    return r.json();
  },

  createDebate: async (topic, mode) => {
    const result = await api.createDebate(topic, mode);
    set({
      session: {
        id: result.id,
        topic: result.topic,
        status: 'running' as const,
        current_round: 0,
        current_exchange: 0,
        config: { max_rounds: 5, max_exchanges_per_round: 10, mode: mode as any, models: {} },
        created_at: new Date().toISOString(),
        completed_at: null,
      },
      messages: [],
      currentDimension: null,
    });
    return result.id;
  },

  loadDebate: async (id) => {
    const data = await api.getDebate(id);
    set({
      session: data.session,
      messages: data.messages,
    });
  },

  loadHistory: async () => {
    const sessions = await api.listDebates();
    set({ history: sessions });
  },

  handleEvent: (event) => {
    const state = get();

    switch (event.type) {
      case 'health_check':
        // Health check in progress
        break;

      case 'model_fallback':
        // Model fallback applied
        console.warn('Model fallback:', event.data);
        break;

      case 'message_start':
        set({ isStreaming: true, streamingRole: event.role || null, streamingContent: '' });
        break;

      case 'message_chunk':
        set({ streamingContent: state.streamingContent + (event.content || '') });
        break;

      case 'message_complete':
        if (event.content && event.role) {
          const msg: Message = {
            id: `evt_${Date.now()}_${event.role}`,
            session_id: state.session?.id || '',
            round_id: 'evt',
            role: event.role,
            round_number: event.round_number || 0,
            exchange_number: event.exchange_number || 0,
            content: event.content,
            audio_url: event.audio_url || null,
            message_type: (event as any).message_type || event.type,
            token_count: null,
            timestamp: event.timestamp || new Date().toISOString(),
          };
          set({
            messages: [...state.messages, msg],
            isStreaming: false,
            streamingRole: null,
            streamingContent: '',
          });
        }
        break;

      case 'round_change':
        if (state.session) {
          set({
            session: {
              ...state.session,
              current_round: event.round_number || state.session.current_round,
            },
          });
        }
        break;

      case 'exchange_update':
        if (state.session) {
          set({
            session: {
              ...state.session,
              current_exchange: event.exchange_number || state.session.current_exchange,
            },
          });
        }
        break;

      case 'debate_completed':
        if (state.session) {
          set({
            session: { ...state.session, status: 'completed' },
          });
        }
        break;

      case 'state_change':
        if (event.state && state.session) {
          set({
            session: { ...state.session, status: event.state as any },
          });
        }
        break;

      case 'error':
        if (state.session) {
          set({
            session: { ...state.session, status: 'error' },
          });
        }
        break;
    }
  },

  pause: async () => {
    const { session } = get();
    if (session) {
      await api.pauseDebate(session.id);
      set({ session: { ...session, status: 'paused' } });
    }
  },

  resume: async () => {
    const { session } = get();
    if (session) {
      await api.resumeDebate(session.id);
      set({ session: { ...session, status: 'running' } });
    }
  },

  stop: async () => {
    const { session } = get();
    if (session) {
      await api.stopDebate(session.id);
      set({ session: { ...session, status: 'stopped' } });
    }
  },

  skipRound: async () => {
    const { session } = get();
    if (session) {
      await api.skipRound(session.id);
    }
  },

  reset: () => {
    set({
      session: null,
      messages: [],
      currentDimension: null,
      isStreaming: false,
      streamingRole: null,
      streamingContent: '',
    });
  },
}));
