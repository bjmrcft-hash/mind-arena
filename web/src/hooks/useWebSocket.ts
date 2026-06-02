import { useEffect, useRef, useCallback } from 'react';
import type { DebateEvent } from '../types/debate';

export function useWebSocket(
  sessionId: string | null,
  onEvent: (event: DebateEvent) => void,
) {
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!sessionId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/debate/${sessionId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WS connected:', sessionId);
    };

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as DebateEvent;
        onEvent(event);
      } catch {
        console.error('WS parse error:', e.data);
      }
    };

    ws.onclose = () => {
      console.log('WS disconnected');
    };

    ws.onerror = (e) => {
      console.error('WS error:', e);
    };
  }, [sessionId, onEvent]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { send };
}
