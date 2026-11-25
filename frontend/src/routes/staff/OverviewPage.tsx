import { useCallback, useEffect, useState } from "react";

import { Card } from "../../components/ui/Card";
import { getOverview, OverviewResponse } from "../../lib/api";
import { useQueueSocket } from "../../lib/useQueueSocket";

const STAT_LABELS: { key: keyof OverviewResponse; label: string }[] = [
  { key: "total_registered_today", label: "Registered Today" },
  { key: "currently_waiting", label: "Currently Waiting" },
  { key: "being_served", label: "Being Served" },
  { key: "completed_today", label: "Completed" },
  { key: "active_counters", label: "Active Counters" },
];

export default function OverviewPage() {
  const [data, setData] = useState<OverviewResponse | null>(null);

  const refresh = useCallback(() => {
    getOverview().then(setData).catch(() => undefined);
  }, []);

  const { refreshSignal } = useQueueSocket();

  useEffect(() => {
    refresh();
  }, [refresh, refreshSignal]);

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-slate-900">Overview</h1>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {STAT_LABELS.map(({ key, label }) => (
          <Card key={key} className="text-center">
            <div className="text-3xl font-bold text-slate-900">{data ? String(data[key]) : "—"}</div>
            <div className="text-sm text-slate-500 mt-1">{label}</div>
          </Card>
        ))}
      </div>

      <Card>
        <h2 className="font-semibold text-slate-800 mb-4">Current token at each counter</h2>
        <div className="grid grid-cols-3 gap-4">
          {data &&
            Object.entries(data.counters_now_serving).map(([name, tokenNumber]) => (
              <div key={name} className="border border-slate-200 rounded-xl p-4 text-center">
                <div className="text-sm text-slate-500">{name}</div>
                <div className="text-2xl font-bold text-slate-900 mt-1">{tokenNumber ?? "—"}</div>
              </div>
            ))}
        </div>
      </Card>
    </div>
  );
}
