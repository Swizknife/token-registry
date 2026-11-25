import { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { useQueueSocket } from "../../lib/useQueueSocket";
import { useAuth } from "./AuthContext";

const NAV_ITEMS = [
  { to: "/staff/overview", label: "Overview" },
  { to: "/staff/queue", label: "Queue" },
  { to: "/staff/counters", label: "Counters" },
];

export default function StaffLayout({ children }: { children: ReactNode }) {
  const { username, role, logout } = useAuth();
  const { connected } = useQueueSocket();

  return (
    <div className="h-screen w-screen flex bg-slate-100">
      <aside className="w-60 bg-slate-900 text-white flex flex-col">
        <div className="p-6 border-b border-slate-800">
          <div className="font-bold text-lg">Queue Control</div>
          <div className="text-slate-400 text-sm mt-1">
            {username} <span className="uppercase text-xs">({role})</span>
          </div>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-600 text-white" : "text-slate-300 hover:bg-slate-800"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-800 space-y-3">
          <div className={`text-xs flex items-center gap-2 ${connected ? "text-emerald-400" : "text-red-400"}`}>
            <span className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-400" : "bg-red-400"}`} />
            {connected ? "Live" : "Reconnecting…"}
          </div>
          <button onClick={logout} className="text-sm text-slate-400 hover:text-white">
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto p-8">{children}</main>
    </div>
  );
}
