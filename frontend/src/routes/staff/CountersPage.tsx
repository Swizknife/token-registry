import { useCallback, useEffect, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { ApiError, callNext, completeToken, CounterResponse, listCounters, markServing, recallToken, skipToken } from "../../lib/api";
import { useQueueSocket } from "../../lib/useQueueSocket";

export default function CountersPage() {
  const [counters, setCounters] = useState<CounterResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [confirmSkip, setConfirmSkip] = useState<number | null>(null);

  const refresh = useCallback(() => {
    listCounters().then(setCounters).catch(() => undefined);
  }, []);

  const { refreshSignal } = useQueueSocket();

  useEffect(() => {
    refresh();
  }, [refresh, refreshSignal]);

  const runAction = async (counterId: number, fn: () => Promise<unknown>) => {
    setBusyId(counterId);
    setError(null);
    try {
      await fn();
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed");
    } finally {
      setBusyId(null);
      setConfirmSkip(null);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Counters</h1>

      {error && (
        <div className="bg-red-50 text-red-700 border border-red-200 rounded-xl px-4 py-3" role="alert">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {counters.map((counter) => {
          const hasToken = counter.current_token_id != null;
          return (
            <Card key={counter.counter_id} className="space-y-4">
              <div>
                <div className="flex items-center justify-between">
                  <h2 className="font-bold text-lg text-slate-900">{counter.counter_name}</h2>
                  <span className="text-xs uppercase text-slate-400">{counter.counter_status}</span>
                </div>
                <p className="text-sm text-slate-500">{counter.assigned_service ?? "Any service"}</p>
              </div>

              <div className="text-center bg-slate-50 rounded-xl py-6">
                <div className="text-sm text-slate-400">Current Token</div>
                <div className="text-4xl font-black text-slate-900 mt-1">
                  {counter.current_token_number ?? "—"}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Button
                  size="md"
                  disabled={hasToken || busyId === counter.counter_id}
                  onClick={() => runAction(counter.counter_id, () => callNext(counter.counter_id))}
                >
                  Call Next
                </Button>
                <Button
                  variant="secondary"
                  size="md"
                  disabled={!hasToken || busyId === counter.counter_id}
                  onClick={() =>
                    runAction(counter.counter_id, () => recallToken(counter.counter_id, counter.current_token_id!))
                  }
                >
                  Recall
                </Button>
                <Button
                  variant="secondary"
                  size="md"
                  disabled={!hasToken || busyId === counter.counter_id}
                  onClick={() =>
                    runAction(counter.counter_id, () => markServing(counter.counter_id, counter.current_token_id!))
                  }
                >
                  Serving
                </Button>
                <Button
                  size="md"
                  disabled={!hasToken || busyId === counter.counter_id}
                  onClick={() =>
                    runAction(counter.counter_id, () => completeToken(counter.counter_id, counter.current_token_id!))
                  }
                >
                  Complete
                </Button>
              </div>

              {confirmSkip === counter.counter_id ? (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-slate-500">Skip this token?</span>
                  <button
                    className="text-red-600 font-semibold hover:underline"
                    onClick={() =>
                      runAction(counter.counter_id, () => skipToken(counter.counter_id, counter.current_token_id!))
                    }
                  >
                    Yes, skip
                  </button>
                  <button className="text-slate-400 hover:underline" onClick={() => setConfirmSkip(null)}>
                    Cancel
                  </button>
                </div>
              ) : (
                <Button
                  variant="danger"
                  size="md"
                  disabled={!hasToken || busyId === counter.counter_id}
                  onClick={() => setConfirmSkip(counter.counter_id)}
                  className="w-full"
                >
                  Skip
                </Button>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
