export interface DebateConfig {
  max_rounds: number;
  max_exchanges_per_round: number;
  mode: 'quick' | 'standard' | 'deep';
  models: Record<string, string>;
}

export interface DebateSession {
  id: string;
  topic: string;
  status: 'idle' | 'running' | 'paused' | 'completed' | 'stopped' | 'error';
  current_round: number;
  current_exchange: number;
  config: DebateConfig;
  created_at: string;
  completed_at: string | null;
}

export interface Message {
  id: string;
  session_id: string;
  round_id: string;
  role: 'A' | 'B' | 'C';
  round_number: number;
  exchange_number: number;
  content: string;
  audio_url: string | null;
  message_type: string;
  model?: string | null;
  token_count: number | null;
  timestamp: string;
}

export interface DebateEvent {
  type: string;
  message_type?: string;
  role?: 'A' | 'B' | 'C';
  content?: string;
  round_number?: number;
  exchange_number?: number;
  dimension?: string;
  audio_url?: string;
  state?: string;
  data?: Record<string, unknown>;
  timestamp?: string;
}

export const ROLE_INFO: Record<string, { name: string; color: string; icon: string }> = {
  A: { name: '主持人 A', color: 'cyan', icon: '🎤' },
  B: { name: '正方 B', color: 'green', icon: '🟩' },
  C: { name: '反方 C', color: 'red', icon: '🟥' },
};

export const MSG_TYPE_LABELS: Record<string, string> = {
  topic_intro: '话题拆解',
  opening: '开场陈述',
  argument: '论点',
  rebuttal: '反驳',
  summary: '轮次总结',
  level_up: '维度提升',
  verdict: '终场总结',
};
