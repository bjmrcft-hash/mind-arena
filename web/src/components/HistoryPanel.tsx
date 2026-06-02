import { useEffect, useState, useCallback } from 'react';
import { useDebateStore } from '../stores/debateStore';

interface Props {
  onSelect: (id: string) => void;
}

export function HistoryPanel({ onSelect }: Props) {
  const {
    history, loadHistory, deleteDebate,
    searchQuery, setSearchQuery,
    sortOrder, setSortOrder,
  } = useDebateStore();

  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const handleDelete = useCallback(async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('确定删除这条辩论记录？')) return;
    setDeleting(id);
    try {
      await deleteDebate(id);
    } finally {
      setDeleting(null);
    }
  }, [deleteDebate]);

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
        <h3 className="text-sm font-medium text-gray-400 mb-2">📋 历史辩论</h3>
        {/* 搜索 + 排序 */}
        <div className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="🔍 搜索话题..."
            className="flex-1 px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded
                       text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
            className="px-2 py-1 text-xs bg-gray-800 border border-gray-700 rounded text-gray-200
                       focus:outline-none focus:border-cyan-500"
          >
            <option value="newest">时间↓</option>
            <option value="oldest">时间↑</option>
            <option value="name_asc">名称A-Z</option>
            <option value="name_desc">名称Z-A</option>
          </select>
        </div>
        {/* 搜索结果反馈 */}
        {searchQuery && (
          <div className="mt-1 text-xs text-gray-500">
            {history.length > 0 ? `找到 ${history.length} 条记录` : '无匹配结果'}
          </div>
        )}
      </div>
      <div className="divide-y divide-gray-800/50 max-h-60 overflow-y-auto">
        {history.length === 0 ? (
          <div className="px-3 py-4 text-center text-gray-500 text-sm">
            {searchQuery ? '无匹配结果' : '暂无记录'}
          </div>
        ) : (
          history.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelect(s.id)}
              className="w-full px-3 py-2 text-left hover:bg-gray-800/30 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-2">
                <span>{statusEmoji[s.status] || '⏳'}</span>
                <span className="text-sm text-gray-200 truncate flex-1">{s.topic}</span>
                <span className="text-xs text-gray-500">
                  {new Date(s.created_at).toLocaleDateString()}
                </span>
                <button
                  onClick={(e) => handleDelete(s.id, e)}
                  disabled={deleting === s.id}
                  className="px-1.5 py-0.5 text-xs text-red-400 hover:bg-red-500/20 rounded transition-colors disabled:opacity-50"
                  title="删除"
                >
                  {deleting === s.id ? '⏳' : '🗑'}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
