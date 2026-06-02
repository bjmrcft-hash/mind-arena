import { ROLE_INFO, MSG_TYPE_LABELS } from '../types/debate';
import type { Message } from '../types/debate';

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const info = ROLE_INFO[message.role] || ROLE_INFO.A;
  const typeLabel = MSG_TYPE_LABELS[message.message_type] || message.message_type;

  const borderColor =
    message.role === 'A' ? 'border-cyan-500/30' :
    message.role === 'B' ? 'border-green-500/30' :
    'border-red-500/30';

  const bgColor =
    message.role === 'A' ? 'bg-cyan-500/5' :
    message.role === 'B' ? 'bg-green-500/5' :
    'bg-red-500/5';

  const nameColor =
    message.role === 'A' ? 'text-cyan-400' :
    message.role === 'B' ? 'text-green-400' :
    'text-red-400';

  // Extract short model name for display
  const modelShort = message.model ? message.model.split('/').pop() : null;

  return (
    <div className={`rounded-lg border ${borderColor} ${bgColor} p-4`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">{info.icon}</span>
        <span className={`font-semibold ${nameColor}`}>{info.name}</span>
        <span className="text-xs text-gray-500 px-2 py-0.5 bg-gray-800 rounded">
          {typeLabel}
        </span>
        {modelShort && (
          <span className="text-xs text-purple-400 px-2 py-0.5 bg-purple-500/10 rounded border border-purple-500/20">
            🤖 {modelShort}
          </span>
        )}
        {message.round_number > 0 && (
          <span className="text-xs text-gray-500">
            R{message.round_number}
            {message.exchange_number > 0 && ` · #${message.exchange_number}`}
          </span>
        )}
      </div>
      <div className="text-gray-200 leading-relaxed whitespace-pre-wrap text-sm">
        {message.content}
      </div>
      {message.audio_url && (
        <audio controls src={message.audio_url} className="mt-2 w-full max-w-xs h-8" />
      )}
    </div>
  );
}
