import { useCallback, useEffect, useRef, useState } from "react";

import { getPublicDisplay, PublicDisplayResponse } from "../../lib/api";
import { useQueueSocket } from "../../lib/useQueueSocket";

export default function DisplayPage() {
  const [data, setData] = useState<PublicDisplayResponse | null>(null);
  const [banner, setBanner] = useState<{ tokenNumber: string; counterName: string } | null>(null);
  const prevServing = useRef<Record<number, string | null>>({});

  const refresh = useCallback(() => {
    getPublicDisplay()
      .then(setData)
      .catch(() => {
        /* transient fetch failure; next poll/refreshSignal retries */
      });
  }, []);

  const { connected, refreshSignal } = useQueueSocket((event) => {
    if (event.type === "token.called") {
      const payload = event.payload as { token_number: string; counter_name: string };
      setBanner({ tokenNumber: payload.token_number, counterName: payload.counter_name });
      const audio = new AudioContext();
      const osc = audio.createOscillator();
      osc.frequency.value = 880;
      osc.connect(audio.destination);
      osc.start();
      setTimeout(() => {
        osc.stop();
        audio.close();
      }, 220);
      setTimeout(() => setBanner(null), 8000);
    }
  });

  useEffect(() => {
    refresh();
  }, [refresh, refreshSignal]);

  // Also poll periodically as a safety net in case a WS message is missed.
  useEffect(() => {
    const interval = setInterval(refresh, 15000);
    return () => clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    if (!data) return;
    prevServing.current = Object.fromEntries(data.now_serving.map((r) => [r.counter_id, r.token_number]));
  }, [data]);

  return (
    <div className="h-screen w-screen bg-slate-950 text-white flex flex-col p-10 overflow-hidden">
      <header className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Live Queue</h1>
        <span
          className={`text-sm px-3 py-1 rounded-full ${connected ? "bg-emerald-500/20 text-emerald-300" : "bg-red-500/20 text-red-300"}`}
        >
          {connected ? "Live" : "Reconnecting…"}
        </span>
      </header>

      {banner && (
        <div
          className="mb-8 bg-amber-400 text-slate-900 rounded-3xl px-10 py-8 text-center animate-pulse"
          role="alert"
          aria-live="assertive"
        >
          <div className="text-6xl font-black">TOKEN {banner.tokenNumber}</div>
          <div className="text-3xl font-bold mt-2">PLEASE PROCEED TO {banner.counterName.toUpperCase()}</div>
        </div>
      )}

      <section className="mb-10">
        <h2 className="text-xl font-semibold text-slate-400 mb-4 uppercase tracking-wide">Now Serving</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
          {data?.now_serving.map((row) => (
            <div
              key={row.counter_id}
              className={`rounded-3xl p-8 text-center border-2 ${
                row.token_number ? "border-brand-400 bg-brand-500/10" : "border-slate-800 bg-slate-900"
              }`}
            >
              <div className="text-lg text-slate-400 mb-2">{row.counter_name}</div>
              <div className="text-6xl font-black">{row.token_number ?? "—"}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-xl font-semibold text-slate-400 mb-4 uppercase tracking-wide">Upcoming</h2>
        <div className="flex flex-wrap items-center gap-4 text-3xl font-bold">
          {data?.upcoming.length ? (
            data.upcoming.map((num, i) => (
              <span key={num} className="flex items-center gap-4">
                <span className="bg-slate-800 rounded-xl px-5 py-3">{num}</span>
                {i < data.upcoming.length - 1 && <span className="text-slate-600">→</span>}
              </span>
            ))
          ) : (
            <span className="text-slate-500 text-xl">No one waiting</span>
          )}
        </div>
      </section>

      <section className="mt-auto">
        <h2 className="text-xl font-semibold text-slate-400 mb-3 uppercase tracking-wide">Recently Completed</h2>
        <div className="flex flex-wrap gap-3 text-xl text-slate-400">
          {data?.recently_completed.length
            ? data.recently_completed.map((num) => (
                <span key={num} className="bg-slate-900 rounded-lg px-4 py-2">
                  {num}
                </span>
              ))
            : <span className="text-slate-600">None yet today</span>}
        </div>
      </section>
    </div>
  );
}
