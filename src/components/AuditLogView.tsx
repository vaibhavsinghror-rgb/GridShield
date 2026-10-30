import React from "react";
import { History, User } from "lucide-react";
import { AuditEvent } from "../types";

interface AuditLogViewProps {
  logs: AuditEvent[];
}

export const AuditLogView: React.FC<AuditLogViewProps> = ({ logs }) => {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between pb-5 border-b border-gray-800 mb-5">
        <div>
          <h2 className="text-base font-bold text-white flex items-center space-x-2">
            <History className="w-5 h-5 text-emerald-400" />
            <span>Immutable Application Audit Log & Safety Governor Stream</span>
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            Tamper-evident record of all simulated manual dispatch overrides, safety filter interventions, and controller mode switches.
          </p>
        </div>
        <span className="text-xs px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
          Append-Only Mode
        </span>
      </div>

      {logs.length === 0 ? (
        <div className="text-center py-12 text-gray-500 text-sm">
          No manual overrides or safety violations recorded. System running in nominal autonomous dispatch mode.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 uppercase tracking-wider">
                <th className="pb-3 font-semibold">Timestamp</th>
                <th className="pb-3 font-semibold">Actor</th>
                <th className="pb-3 font-semibold">Event Action</th>
                <th className="pb-3 font-semibold">Justification / Reason</th>
                <th className="pb-3 font-semibold">State Transition</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 font-mono text-gray-300">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-850/50 transition-colors">
                  <td className="py-3 text-gray-400 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </td>
                  <td className="py-3 text-emerald-400 font-semibold flex items-center space-x-1.5">
                    <User className="w-3.5 h-3.5" />
                    <span>{log.actor}</span>
                  </td>
                  <td className="py-3">
                    <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-200 border border-gray-700">
                      {log.action}
                    </span>
                  </td>
                  <td className="py-3 font-sans text-gray-300 max-w-xs truncate" title={log.reason}>
                    {log.reason}
                  </td>
                  <td className="py-3 text-gray-400 max-w-xs truncate text-[11px]" title={log.after_state}>
                    {log.after_state}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
