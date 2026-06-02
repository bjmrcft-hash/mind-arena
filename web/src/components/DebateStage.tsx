import { useEffect, useRef, useState } from 'react';
import type { ReactElement } from 'react';
import { useDebateStore } from '../stores/debateStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { ControlPanel } from './ControlPanel';
import { StatusBar } from './StatusBar';
import { ROLE_INFO } from '../types/debate';
import type { Message } from '../types/debate';

// ── Human-like character avatar ──
function CharacterAvatar({
  role,
  isActive,
  isSpeaking,
  size = 'md',
  modelName,
}: {
  role: string;
  isActive: boolean;
  isSpeaking: boolean;
  size?: 'sm' | 'md' | 'lg';
  modelName?: string;
}) {
  const info = ROLE_INFO[role] || ROLE_INFO.A;

  // Human-like SVG avatars
  const avatars: Record<string, ReactElement> = {
    A: (
      <svg viewBox="0 0 64 64" className="w-full h-full">
        {/* Hair */}
        <ellipse cx="32" cy="18" rx="16" ry="14" fill="#1e293b" />
        {/* Face */}
        <ellipse cx="32" cy="26" rx="12" ry="13" fill="#fcd9b6" />
        {/* Eyes */}
        <ellipse cx="26" cy="24" rx="2" ry="2.5" fill="#1e293b" />
        <ellipse cx="38" cy="24" rx="2" ry="2.5" fill="#1e293b" />
        <circle cx="26.8" cy="23.5" r="0.8" fill="white" />
        <circle cx="38.8" cy="23.5" r="0.8" fill="white" />
        {/* Eyebrows */}
        <path d="M22 20 Q26 17 30 20" stroke="#1e293b" strokeWidth="1.2" fill="none" />
        <path d="M34 20 Q38 17 42 20" stroke="#1e293b" strokeWidth="1.2" fill="none" />
        {/* Nose */}
        <path d="M31 27 Q32 29 33 27" stroke="#d4a574" strokeWidth="0.8" fill="none" />
        {/* Mouth - slight smile */}
        <path d="M27 32 Q32 36 37 32" stroke="#c0392b" strokeWidth="1.2" fill="none" />
        {/* Glasses */}
        <rect x="20" y="20" width="10" height="8" rx="2" fill="none" stroke="#64748b" strokeWidth="1" />
        <rect x="34" y="20" width="10" height="8" rx="2" fill="none" stroke="#64748b" strokeWidth="1" />
        <line x1="30" y1="24" x2="34" y2="24" stroke="#64748b" strokeWidth="1" />
        {/* Suit collar */}
        <path d="M20 42 L28 36 L32 40 L36 36 L44 42 L44 54 L20 54 Z" fill="#0e7490" />
        <path d="M28 36 L32 42 L36 36" fill="#164e63" />
        {/* Tie */}
        <path d="M31 40 L32 48 L33 40" fill="#f59e0b" />
      </svg>
    ),
    B: (
      <svg viewBox="0 0 64 64" className="w-full h-full">
        {/* Hair - short spiky */}
        <path d="M16 20 L20 8 L26 16 L32 6 L38 16 L44 8 L48 20" fill="#2d1810" />
        <ellipse cx="32" cy="20" rx="16" ry="12" fill="#2d1810" />
        {/* Face */}
        <ellipse cx="32" cy="26" rx="12" ry="13" fill="#e8c39e" />
        {/* Eyes - confident */}
        <ellipse cx="26" cy="24" rx="2.2" ry="2" fill="#1e293b" />
        <ellipse cx="38" cy="24" rx="2.2" ry="2" fill="#1e293b" />
        <circle cx="27" cy="23.5" r="0.8" fill="white" />
        <circle cx="39" cy="23.5" r="0.8" fill="white" />
        {/* Eyebrows - determined */}
        <path d="M22 19 L30 20" stroke="#2d1810" strokeWidth="1.5" fill="none" />
        <path d="M34 20 L42 19" stroke="#2d1810" strokeWidth="1.5" fill="none" />
        {/* Nose */}
        <path d="M31 27 Q32 29 33 27" stroke="#c9a074" strokeWidth="0.8" fill="none" />
        {/* Mouth - slight grin */}
        <path d="M27 32 Q30 35 32 33 Q34 35 37 32" stroke="#b5453a" strokeWidth="1" fill="none" />
        {/* Collar */}
        <path d="M18 44 L26 37 L32 42 L38 37 L46 44 L46 56 L18 56 Z" fill="#059669" />
        <path d="M26 37 L32 43 L38 37" fill="#047857" />
        {/* No tie - casual */}
        <circle cx="32" cy="38" r="1.5" fill="#fbbf24" />
      </svg>
    ),
    C: (
      <svg viewBox="0 0 64 64" className="w-full h-full">
        {/* Hair - styled */}
        <ellipse cx="32" cy="17" rx="17" ry="13" fill="#4a1a1a" />
        <path d="M15 20 Q20 10 32 8 Q44 10 49 20" fill="#4a1a1a" />
        {/* Face */}
        <ellipse cx="32" cy="26" rx="12" ry="13" fill="#f0d5b0" />
        {/* Eyes - sharp */}
        <ellipse cx="26" cy="24" rx="2" ry="2.2" fill="#1e293b" />
        <ellipse cx="38" cy="24" rx="2" ry="2.2" fill="#1e293b" />
        <circle cx="26.5" cy="23.5" r="0.7" fill="white" />
        <circle cx="38.5" cy="23.5" r="0.7" fill="white" />
        {/* Eyebrows - analytical */}
        <path d="M22 19 Q26 17 30 19" stroke="#4a1a1a" strokeWidth="1.3" fill="none" />
        <path d="M34 19 Q38 17 42 19" stroke="#4a1a1a" strokeWidth="1.3" fill="none" />
        {/* Nose */}
        <path d="M31 27 Q32 29 33 27" stroke="#d4a574" strokeWidth="0.8" fill="none" />
        {/* Mouth - neutral/thinking */}
        <line x1="27" y1="32" x2="37" y2="32" stroke="#b5453a" strokeWidth="1.2" />
        {/* Collar */}
        <path d="M18 44 L26 37 L32 42 L38 37 L46 44 L46 56 L18 56 Z" fill="#e11d48" />
        <path d="M26 37 L32 43 L38 37" fill="#be123c" />
        {/* Pin */}
        <circle cx="28" cy="44" r="1.2" fill="#fbbf24" />
      </svg>
    ),
  };

  const sizeClasses = { sm: 'w-10 h-10', md: 'w-14 h-14', lg: 'w-20 h-20' };
  const shadowColors: Record<string, string> = {
    A: 'shadow-cyan-500/40',
    B: 'shadow-emerald-500/40',
    C: 'shadow-rose-500/40',
  };
  const ringColors: Record<string, string> = {
    A: 'ring-cyan-400/60',
    B: 'ring-emerald-400/60',
    C: 'ring-rose-400/60',
  };

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div
        className={`
          relative ${sizeClasses[size]} rounded-full overflow-hidden
          bg-gradient-to-br from-gray-700 to-gray-900
          transition-all duration-500
          ${isActive ? `ring-2 ${ringColors[role]} shadow-xl ${shadowColors[role]} scale-110` : 'opacity-70 scale-100'}
          ${isSpeaking ? 'animate-bounce' : ''}
        `}
        style={{ animationDuration: isSpeaking ? '0.5s' : undefined }}
      >
        {avatars[role] || avatars.A}
      </div>
      <span className={`text-xs font-semibold tracking-wide transition-colors ${isActive ? 'text-gray-200' : 'text-gray-600'}`}>
        {info.name}
      </span>
      {modelName && (
        <span className={`text-[10px] transition-colors ${isActive ? 'text-gray-400' : 'text-gray-600'}`}>
          {modelName}
        </span>
      )}
    </div>
  );
}

// ── Speech bubble with role styling ──
function SpeechBubble({
  message,
  isStreaming,
  streamContent,
  compact = false,
}: {
  message: Message | null;
  isStreaming: boolean;
  streamContent: string;
  compact?: boolean;
}) {
  if (!message && !isStreaming) return null;

  const role = message?.role || 'A';
  const content = message?.content || streamContent;

  const borderColors: Record<string, string> = {
    A: 'border-cyan-500/20',
    B: 'border-emerald-500/20',
    C: 'border-rose-500/20',
  };
  const bgColors: Record<string, string> = {
    A: 'bg-gradient-to-br from-cyan-950/30 to-gray-900/50',
    B: 'bg-gradient-to-br from-emerald-950/30 to-gray-900/50',
    C: 'bg-gradient-to-br from-rose-950/30 to-gray-900/50',
  };
  const accentColors: Record<string, string> = {
    A: 'text-cyan-400',
    B: 'text-emerald-400',
    C: 'text-rose-400',
  };
  const barColors: Record<string, string> = {
    A: 'bg-cyan-500',
    B: 'bg-emerald-500',
    C: 'bg-rose-500',
  };

  return (
    <div className={`rounded-xl border ${borderColors[role]} ${bgColors[role]} backdrop-blur-sm animate-in relative overflow-hidden`}>
      {/* Accent bar */}
      <div className={`absolute left-0 top-0 bottom-0 w-0.5 ${barColors[role]}`} />

      <div className={`${compact ? 'px-3 py-2' : 'px-4 py-3'}`}>
        {/* Header */}
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-sm">{ROLE_INFO[role]?.icon}</span>
          <span className={`font-semibold text-xs ${accentColors[role]}`}>
            {ROLE_INFO[role]?.name}
          </span>
          {message?.message_type && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800/80 text-gray-500 border border-gray-700/50">
              {message.message_type === 'level_up' ? '维度提升' :
               message.message_type === 'summary' ? '轮次总结' :
               message.message_type === 'argument' ? '论点' :
               message.message_type === 'rebuttal' ? '反驳' :
               message.message_type === 'topic_intro' ? '话题拆解' :
               message.message_type === 'opening' ? '开场' :
               message.message_type === 'verdict' ? '终场' :
               message.message_type}
            </span>
          )}
          {isStreaming && <span className="text-[10px] text-gray-500 animate-pulse ml-auto">生成中...</span>}
        </div>

        {/* Content */}
        <div className={`text-gray-200 ${compact ? 'text-xs' : 'text-sm'} leading-relaxed whitespace-pre-wrap`}>
          {content}
          {isStreaming && <span className="inline-block w-0.5 h-3.5 bg-cyan-400 animate-pulse ml-0.5" />}
        </div>
      </div>
    </div>
  );
}

// ── Exchange pair (B left, C right, aligned) ──
function ExchangePair({
  bMessage,
  cMessage,
  exchangeNum,
}: {
  bMessage: Message | null;
  cMessage: Message | null;
  exchangeNum: number;
}) {
  return (
    <div className="grid grid-cols-[1fr_auto_1fr] gap-4 items-start">
      <div className="flex justify-end">
        {bMessage && <SpeechBubble message={bMessage} isStreaming={false} streamContent="" />}
      </div>
      <div className="flex flex-col items-center pt-3">
        <div className="w-7 h-7 rounded-full bg-gray-800/80 border border-gray-700/50 flex items-center justify-center text-[10px] text-gray-500 font-mono">
          {exchangeNum}
        </div>
      </div>
      <div>
        {cMessage && <SpeechBubble message={cMessage} isStreaming={false} streamContent="" />}
      </div>
    </div>
  );
}

// ── Table with CSS texture ──
function OvalTable({ dimension }: { dimension: string | null }) {
  return (
    <div className="relative mx-6">
      <div
        className="w-64 h-24 rounded-[50%] border-2 border-amber-900/30 flex items-center justify-center overflow-hidden"
        style={{
          background: `
            radial-gradient(ellipse at 35% 25%, rgba(255,255,255,0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 65% 75%, rgba(0,0,0,0.3) 0%, transparent 50%),
            repeating-linear-gradient(
              90deg,
              rgba(120,80,40,0.15) 0px,
              rgba(90,60,30,0.08) 3px,
              rgba(120,80,40,0.12) 6px,
              rgba(80,50,25,0.1) 9px,
              rgba(120,80,40,0.15) 12px
            ),
            linear-gradient(180deg, #2a1f14 0%, #1a120a 40%, #0f0a06 100%)
          `,
          boxShadow: 'inset 0 2px 8px rgba(255,255,255,0.05), inset 0 -4px 12px rgba(0,0,0,0.5), 0 4px 20px rgba(0,0,0,0.4)',
        }}
      >
        {/* Center label */}
        <div className="relative z-10 text-center">
          <div className="text-xs text-amber-200/40 font-medium tracking-[0.3em]">辩 论 桌</div>
          {dimension && (
            <div className="text-[11px] text-cyan-400/50 mt-0.5 max-w-[200px] truncate">📐 {dimension}</div>
          )}
        </div>
      </div>
      {/* Top edge highlight */}
      <div
        className="absolute top-0 left-[10%] right-[10%] h-px"
        style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)' }}
      />
    </div>
  );
}

// ── Main Debate Stage ──
export function DebateStage() {
  const {
    session, messages, currentDimension, isStreaming, streamingRole, streamingContent,
    handleEvent, pause, resume, stop, skipRound,
  } = useDebateStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [activeSpeaker, setActiveSpeaker] = useState<string | null>(null);

  useWebSocket(session?.id || null, handleEvent);

  useEffect(() => {
    if (isStreaming && streamingRole) {
      setActiveSpeaker(streamingRole);
    } else if (messages.length > 0) {
      setActiveSpeaker(messages[messages.length - 1].role);
    }
  }, [isStreaming, streamingRole, messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  if (!session) return null;

  // ── Categorize messages ──
  const topicIntro = messages.find(m => m.message_type === 'topic_intro');
  const openings = messages.filter(m => m.message_type === 'opening');
  const verdict = messages.find(m => m.message_type === 'verdict');

  // ALL moderator messages (A) that are not topic_intro or verdict
  const moderatorMsgs = messages.filter(
    m => m.role === 'A' && !['topic_intro', 'verdict'].includes(m.message_type)
  );

  // B/C debate messages grouped by round
  const debateMsgs = messages.filter(
    m => m.role !== 'A' && !['opening'].includes(m.message_type)
  );

  // Build timeline: round → { level_up, exchanges[], summary }
  const rounds = new Map<number, {
    levelUp: Message | null;
    exchanges: Map<number, { b: Message | null; c: Message | null }>;
    summary: Message | null;
  }>();

  // First, collect moderator messages per round
  for (const m of moderatorMsgs) {
    const rn = m.round_number;
    if (!rounds.has(rn)) rounds.set(rn, { levelUp: null, exchanges: new Map(), summary: null });
    const r = rounds.get(rn)!;
    if (m.message_type === 'level_up') r.levelUp = m;
    if (m.message_type === 'summary') r.summary = m;
  }

  // Then, collect debate messages per round
  for (const m of debateMsgs) {
    const rn = m.round_number;
    if (!rounds.has(rn)) rounds.set(rn, { levelUp: null, exchanges: new Map(), summary: null });
    const r = rounds.get(rn)!;
    const ex = m.exchange_number;
    if (!r.exchanges.has(ex)) r.exchanges.set(ex, { b: null, c: null });
    const e = r.exchanges.get(ex)!;
    if (m.role === 'B') e.b = m;
    if (m.role === 'C') e.c = m;
  }

  const sortedRounds = [...rounds.entries()].sort(([a], [b]) => a - b);

  return (
    <div className="flex flex-col gap-5 w-full">
      {/* ── Arena Header ── */}
      <div className="flex items-center justify-between px-5 py-3 rounded-xl border border-gray-800 bg-gray-900/80 backdrop-blur">
        <div className="flex items-center gap-3">
          <span className="text-xl">🏟️</span>
          <h2 className="font-semibold text-gray-100 text-lg">{session.topic}</h2>
          <span className={`text-xs px-2 py-0.5 rounded-full border ${
            session.status === 'running' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
            session.status === 'completed' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' :
            'bg-gray-800 text-gray-400 border-gray-700'
          }`}>
            {session.status === 'running' ? '🔴 进行中' :
             session.status === 'completed' ? '✅ 已完成' :
             session.status === 'paused' ? '⏸ 已暂停' : session.status}
          </span>
        </div>
        <ControlPanel
          status={session.status}
          onPause={pause}
          onResume={resume}
          onStop={stop}
          onSkip={skipRound}
        />
      </div>

      {/* ── Status ── */}
      <div className="px-5 py-2 rounded-lg border border-gray-800/50 bg-gray-900/30">
        <StatusBar session={session} dimension={currentDimension} />
      </div>

      {/* ── Debate Arena ── */}
      <div className="relative rounded-2xl border border-gray-800 bg-gradient-to-b from-gray-900/90 via-gray-950/90 to-gray-950 overflow-hidden">

        {/* ── Top: Moderator ── */}
        <div className="relative flex flex-col items-center pt-6 pb-4">
          <CharacterAvatar role="A" isActive={activeSpeaker === 'A'} isSpeaking={isStreaming && streamingRole === 'A'} size="lg" modelName={session.config?.models?.A} />
          <div className="mt-1 text-[10px] text-gray-500 tracking-widest uppercase">主持人</div>
        </div>

        {/* ── Middle: Oval table with B/C ── */}
        <div className="relative flex items-center justify-center px-8 pb-4">
          {/* B on left */}
          <div className="z-10">
            <CharacterAvatar role="B" isActive={activeSpeaker === 'B'} isSpeaking={isStreaming && streamingRole === 'B'} modelName={session.config?.models?.B} />
          </div>

          {/* Oval table */}
          <OvalTable dimension={currentDimension} />

          {/* C on right */}
          <div className="z-10">
            <CharacterAvatar role="C" isActive={activeSpeaker === 'C'} isSpeaking={isStreaming && streamingRole === 'C'} modelName={session.config?.models?.C} />
          </div>
        </div>

        {/* ── Debate Content (wide) ── */}
        <div className="relative px-8 pb-6 space-y-5 max-h-[65vh] overflow-y-auto">
          {/* Topic Intro */}
          {topicIntro && (
            <div className="flex justify-center">
              <div className="w-full max-w-3xl">
                <SpeechBubble message={topicIntro} isStreaming={false} streamContent="" />
              </div>
            </div>
          )}

          {/* Opening statements side by side */}
          {openings.length > 0 && (
            <div className="space-y-2">
              <div className="text-center text-[10px] text-gray-600 uppercase tracking-[0.2em]">开 场 陈 述</div>
              <div className="grid grid-cols-2 gap-6">
                <div className="flex justify-end">
                  {openings.find(m => m.role === 'B') && (
                    <SpeechBubble message={openings.find(m => m.role === 'B')!} isStreaming={false} streamContent="" />
                  )}
                </div>
                <div>
                  {openings.find(m => m.role === 'C') && (
                    <SpeechBubble message={openings.find(m => m.role === 'C')!} isStreaming={false} streamContent="" />
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Rounds */}
          {sortedRounds.map(([rnd, data]) => (
            <div key={rnd} className="space-y-4">
              {/* Round divider */}
              <div className="flex items-center gap-4">
                <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-700/50 to-transparent" />
                <span className="text-[10px] text-gray-500 font-mono tracking-widest">ROUND {rnd}</span>
                <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-700/50 to-transparent" />
              </div>

              {/* Moderator level-up (centered, full width) */}
              {data.levelUp && (
                <div className="flex justify-center">
                  <div className="w-full max-w-4xl">
                    <SpeechBubble message={data.levelUp} isStreaming={false} streamContent="" compact />
                  </div>
                </div>
              )}

              {/* Exchange pairs (B left, C right) */}
              {[...data.exchanges.entries()].sort(([a], [b]) => a - b).map(([ex, pair]) => (
                <ExchangePair
                  key={`${rnd}-${ex}`}
                  bMessage={pair.b}
                  cMessage={pair.c}
                  exchangeNum={ex}
                />
              ))}

              {/* Moderator round summary (centered, full width) */}
              {data.summary && (
                <div className="flex justify-center">
                  <div className="w-full max-w-4xl">
                    <SpeechBubble message={data.summary} isStreaming={false} streamContent="" compact />
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Streaming indicator */}
          {isStreaming && streamingRole && (
            <div className="flex justify-center">
              <div className="w-full max-w-4xl">
                <SpeechBubble message={null} isStreaming={true} streamContent={streamingContent} />
              </div>
            </div>
          )}

          {/* Verdict */}
          {verdict && (
            <div className="space-y-2">
              <div className="flex items-center gap-4">
                <div className="flex-1 h-px bg-gradient-to-r from-transparent via-cyan-700/50 to-transparent" />
                <span className="text-[10px] text-cyan-500 font-mono tracking-widest">终 场 总 结</span>
                <div className="flex-1 h-px bg-gradient-to-r from-transparent via-cyan-700/50 to-transparent" />
              </div>
              <div className="flex justify-center">
                <div className="w-full max-w-4xl">
                  <SpeechBubble message={verdict} isStreaming={false} streamContent="" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* ── Completion banner ── */}
        {session.status === 'completed' && (
          <div className="px-6 py-3 border-t border-gray-800 bg-cyan-500/5 text-center">
            <span className="text-cyan-400 font-medium">✅ 辩论完成</span>
            <a
              href={`/api/debates/${session.id}/export?format=markdown`}
              className="ml-4 text-sm text-gray-400 hover:text-cyan-400 underline transition-colors"
            >
              📥 导出 Markdown
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
