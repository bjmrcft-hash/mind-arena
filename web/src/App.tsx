import { useCallback } from 'react';
import { useDebateStore } from './stores/debateStore';
import { TopicInput } from './components/TopicInput';
import { DebateStage } from './components/DebateStage';
import { HistoryPanel } from './components/HistoryPanel';

export default function App() {
  const { session, createDebate, loadDebate, reset } = useDebateStore();

  const handleStart = useCallback(
    async (topic: string, mode: string) => {
      reset();
      await createDebate(topic, mode);
    },
    [createDebate, reset],
  );

  const handleSelectHistory = useCallback(
    (id: string) => {
      reset();
      loadDebate(id);
    },
    [loadDebate, reset],
  );

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl font-bold">
            <span className="text-cyan-400">🏟️</span> MindArena
          </h1>
          {session && (
            <button
              onClick={reset}
              className="text-sm text-gray-400 hover:text-cyan-400 transition-colors"
            >
              + 新辩论
            </button>
          )}
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-6 flex flex-col gap-6">
        {/* Topic Input */}
        <TopicInput onStart={handleStart} disabled={!!session && session.status === 'running'} />

        {/* Debate Stage */}
        <DebateStage />

        {/* History */}
        {!session && <HistoryPanel onSelect={handleSelectHistory} />}
      </main>
    </div>
  );
}
