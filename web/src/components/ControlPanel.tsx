interface Props {
  status: string;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onSkip: () => void;
}

export function ControlPanel({ status, onPause, onResume, onStop, onSkip }: Props) {
  const isRunning = status === 'running';
  const isPaused = status === 'paused';
  const isActive = isRunning || isPaused;

  return (
    <div className="flex gap-2">
      {isActive && (
        <>
          {isRunning ? (
            <button
              onClick={onPause}
              className="px-3 py-1.5 text-sm bg-yellow-600/20 text-yellow-400 border border-yellow-500/30
                         rounded hover:bg-yellow-600/30 transition-colors"
            >
              ⏸ 暂停
            </button>
          ) : (
            <button
              onClick={onResume}
              className="px-3 py-1.5 text-sm bg-green-600/20 text-green-400 border border-green-500/30
                         rounded hover:bg-green-600/30 transition-colors"
            >
              ▶ 继续
            </button>
          )}
          <button
            onClick={onSkip}
            className="px-3 py-1.5 text-sm bg-blue-600/20 text-blue-400 border border-blue-500/30
                       rounded hover:bg-blue-600/30 transition-colors"
          >
            ⏭ 跳过本轮
          </button>
          <button
            onClick={onStop}
            className="px-3 py-1.5 text-sm bg-red-600/20 text-red-400 border border-red-500/30
                       rounded hover:bg-red-600/30 transition-colors"
          >
            ⏹ 停止
          </button>
        </>
      )}
    </div>
  );
}
