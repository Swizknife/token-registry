import { useCallback, useEffect, useState } from "react";

import { StatusBadge } from "../../components/ui/StatusBadge";
import { listTokens, markAbsent, requeueToken, TokenStaffRow } from "../../lib/api";
import { useQueueSocket } from "../../lib/useQueueSocket";

const STATUSES = ["waiting", "called", "serving", "completed", "skipped", "absent"];

export default function QueuePage() {
  const [rows, setRows] = useState<TokenStaffRow[]>([]);
  const [status, setStatus] = useState("");
  const [service, setService] = useState("");
  const [q, setQ] = useState("");
  const [confirmAction, setConfirmAction] = useState<{ tokenId: number; action: "absent" } | null>(null);

  const refresh = useCallback(() => {
    listTokens({ status: status || undefined, service: service || undefined, q: q || undefined })
      .then(setRows)
      .catch(() => undefined);
  }, [status, service, q]);

  const { refreshSignal } = useQueueSocket();

  useEffect(() => {
    refresh();
  }, [refresh, refreshSignal]);

  const doRequeue = async (tokenId: number) => {
    await requeueToken(tokenId);
    refresh();
  };

  const doAbsent = async (tokenId: number) => {
    await markAbsent(tokenId);
    setConfirmAction(null);
    refresh();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Queue</h1>

      <div className="flex gap-3">
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <input
          placeholder="Filter by service"
          value={service}
          onChange={(e) => setService(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
        <input
          placeholder="Search token number"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-500 uppercase text-xs">
            <tr>
              <th className="px-4 py-3">Token</th>
              <th className="px-4 py-3">Phone</th>
              <th className="px-4 py-3">Purpose</th>
              <th className="px-4 py-3">Registered</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.token_id} className="border-t border-slate-100">
                <td className="px-4 py-3 font-semibold">{row.token_number}</td>
                <td className="px-4 py-3 text-slate-500">{row.phone_masked}</td>
                <td className="px-4 py-3">{row.service_category}</td>
                <td className="px-4 py-3 text-slate-500">
                  {new Date(row.registration_time).toLocaleTimeString()}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={row.status} />
                </td>
                <td className="px-4 py-3 space-x-2">
                  {(row.status === "skipped" || row.status === "absent") && (
                    <button
                      className="text-brand-600 hover:underline"
                      onClick={() => doRequeue(row.token_id)}
                    >
                      Requeue
                    </button>
                  )}
                  {(row.status === "called" || row.status === "serving") &&
                    (confirmAction?.tokenId === row.token_id ? (
                      <>
                        <span className="text-slate-500 text-xs">Confirm?</span>
                        <button className="text-red-600 hover:underline" onClick={() => doAbsent(row.token_id)}>
                          Yes
                        </button>
                        <button className="text-slate-400 hover:underline" onClick={() => setConfirmAction(null)}>
                          No
                        </button>
                      </>
                    ) : (
                      <button
                        className="text-red-600 hover:underline"
                        onClick={() => setConfirmAction({ tokenId: row.token_id, action: "absent" })}
                      >
                        Mark Absent
                      </button>
                    ))}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                  No tokens match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
