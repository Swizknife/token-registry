import { useEffect, useRef, useState } from "react";

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws/queue";

export interface QueueEvent {
  type: string;
  payload: Record<string, unknown>;
}

/**
 * Connects to the realtime queue socket and calls `onEvent` for every
 * message. Also exposes a `connected` flag and a monotonically increasing
 * `refreshSignal` that increments on every event AND on every (re)connect --
 * callers should re-fetch their REST snapshot on `refreshSignal` changes
 * rather than trying to apply events incrementally, so a missed message
 * during a disconnect never leaves the UI stale.
 */
export function useQueueSocket(onEvent?: (event: QueueEvent) => void) {
  const [connected, setConnected] = useState(false);
  const [refreshSignal, setRefreshSignal] = useState(0);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closedByEffect = false;

    const connect = () => {
      socket = new WebSocket(WS_URL);

      socket.onopen = () => {
        setConnected(true);
        setRefreshSignal((n) => n + 1);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as QueueEvent;
          onEventRef.current?.(data);
        } catch {
          /* ignore malformed frame */
        }
        setRefreshSignal((n) => n + 1);
      };

      socket.onclose = () => {
        setConnected(false);
        if (!closedByEffect) {
          reconnectTimer = setTimeout(connect, 2000);
        }
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      closedByEffect = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  return { connected, refreshSignal };
}
