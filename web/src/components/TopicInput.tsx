import { useState, useCallback } from 'react';
import type { FormEvent } from 'react';
import { useDebateStore } from '../stores/debateStore';

interface Props {
  onStart: (topic: string, mode: string) => void;
  disabled: boolean;
}

export function TopicInput({ onStart, disabled }: Props) {
  const [topic, setTopic] = useState('');
  const [mode, setMode] = useState('quick');
  const [healthStatus, setHealthStatus] = useState<Record<string, { model: string; available: boolean; latency_ms: number; provider: string }> | null>(null);
  const [checking, setChecking] = useState(false);

  const { healthCheck } = useDebateStore();

  const handleHealthCheck = useCallback(async () => {
    setChecking(true);
    try {
      const result = await healthCheck() as any;
      if (result.models) {
        setHealthStatus(result.models);
      }
    } catch (e) {
      console.error('Health check failed:', e);
    } finally {
      setChecking(false);
    }
  }, [healthCheck]);

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      if (topic.trim()) {
        onStart(topic.trim(), mode);
        setTopic('');
      }
    },
    [topic, mode, onStart],
  );

  return (
    <div className="flex flex-col gap-3">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="输入辩论话题..."
          disabled={disabled}
          className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg
                     text-gray-100 placeholder-gray-500
                     focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500
                     disabled:opacity-50"
        />
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value)}
          disabled={disabled}
          className="px-3 py-3 bg-gray-800 border border-gray-700 rounded-lg text-gray-100
                     focus:outline-none focus:border-cyan-500
                     disabled:opacity-50"
        >
          <option value="quick">快速 (2轮)</option>
          <option value="standard">标准 (5轮)</option>
          <option value="deep">深度 (8轮)</option>
        </select>
        <button
          type="button"
          onClick={handleHealthCheck}
          disabled={checking}
          className="px-4 py-3 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm rounded-lg
                     disabled:opacity-50 transition-colors"
          title="检查模型状态"
        >
          {checking ? '⏳' : '🔍'}
        </button>
        <button
          type="submit"
          disabled={disabled || !topic.trim()}
          className="px-6 py-3 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg
                     disabled:opacity-50 disabled:cursor-not-allowed
                     transition-colors"
        >
          🚀 开始辩论
        </button>
      </form>

      {/* Model health status */}
      {healthStatus && (
        <div className="flex gap-3 text-xs">
          {Object.entries(healthStatus).map(([role, info]) => (
            <div
              key={role}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border ${
                info.available
                  ? 'bg-green-500/10 border-green-500/20 text-green-400'
                  : 'bg-red-500/10 border-red-500/20 text-red-400'
              }`}
            >
              <span className="font-semibold">{role}</span>
              <span className="text-gray-500">{info.provider}</span>
              <span>{info.available ? `✓ ${info.latency_ms}ms` : '✗ 不可用'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
