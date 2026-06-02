import { useEffect } from 'react';
import { useDebateStore } from '../stores/debateStore';

interface Props {
  onSelect: (id: string) => void;
}

export function HistoryPanel({ onSelect }: Props) {
  const { history, loadHistory } = useDebateStore();

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  if (history.length === 0) return null;

  const statusEmoji: Record<string, string> = {
    completed: '✅',
    running: '🔴',
    paused: '⏸',
    stopped: '⏹',
    error: '❌',
    idle: '⏳',
  };

  return (
    <div className="border border-gray-800 rounded-lg overflow-hidden">
      <div className="px-3 py-2 bg-gray-900/80 border-b border-gray-800">
        <h3 className="text-sm font-medium text-gray-400">📋 历史辩论</h3>
      </div>
      <div className="divide-y divide-gray-800/50 max-h-60 overflow-y-auto">
        {history.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className="w-full px-3 py-2 text-left hover:bg-gray-800/30 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span>{statusEmoji[s.status] || '⏳'}</span>
              <span className="text-sm text-gray-200 truncate flex-1">{s.topic}</span>
              <span className="text-xs text-gray-500">
                {new Date(s.created_at).toLocaleDateString()}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
