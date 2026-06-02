import type { DebateSession } from '../types/debate';

interface Props {
  session: DebateSession | null;
  dimension: string | null;
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  idle: { label: '等待', color: 'text-gray-400' },
  running: { label: '进行中', color: 'text-green-400' },
  paused: { label: '已暂停', color: 'text-yellow-400' },
  completed: { label: '已完成', color: 'text-cyan-400' },
  stopped: { label: '已停止', color: 'text-gray-400' },
  error: { label: '错误', color: 'text-red-400' },
};

export function StatusBar({ session, dimension }: Props) {
  if (!session) return null;

  const st = STATUS_LABELS[session.status] || STATUS_LABELS.idle;

  return (
    <div className="flex items-center gap-4 text-sm">
      <span className={`font-medium ${st.color}`}>
        {session.status === 'running' && '🔴'} {st.label}
      </span>
      <span className="text-gray-500">
        Round {session.current_round}/{session.config.max_rounds}
      </span>
      <span className="text-gray-500">
        交锋 {session.current_exchange}/{session.config.max_exchanges_per_round}
      </span>
      {dimension && (
        <span className="text-purple-400">
          📐 {dimension}
        </span>
      )}
    </div>
  );
}
