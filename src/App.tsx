import { useState, useEffect } from "react";
import { Navbar } from "./components/Navbar";
import { KPICards } from "./components/KPICards";
import { Charts } from "./components/Charts";
import { DispatchPlanner } from "./components/DispatchPlanner";
import { AuditLogView } from "./components/AuditLogView";
import { BenchmarkView } from "./components/BenchmarkView";
import { ManualOverrideModal } from "./components/ManualOverrideModal";
import { fetchTelemetryHistory, fetchAnalyticsSummary, fetchAuditLogs } from "./services/api";
import { TelemetryRecord, AnalyticsSummary, AuditEvent } from "./types";
import { AlertCircle } from "lucide-react";

export function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [telemetry, setTelemetry] = useState<TelemetryRecord[]>([]);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isOverrideModalOpen, setIsOverrideModalOpen] = useState(false);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [telemData, summaryData, logsData] = await Promise.all([
        fetchTelemetryHistory(96),
        fetchAnalyticsSummary(),
        fetchAuditLogs(50),
      ]);
      setTelemetry(telemData);
      setSummary(summaryData);
      setAuditLogs(logsData);
    } catch (err: any) {
      console.error("Failed to load dashboard data:", err);
      setError("Unable to reach backend simulation server. Ensure backend is running at http://localhost:4000.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // 30s background refresh interval
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const currentTelemetry = telemetry.length > 0 ? telemetry[telemetry.length - 1] : null;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col font-sans">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isLoading={isLoading}
        onRefresh={loadData}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center space-x-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <div>
              <p className="font-semibold">Backend Connection Alert</p>
              <p className="text-xs text-rose-400 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Global Real-Time KPI Cards */}
        <KPICards current={currentTelemetry} summary={summary} />

        {/* Dynamic Tab Body */}
        {activeTab === "overview" && <Charts telemetry={telemetry} />}
        {activeTab === "planner" && (
          <DispatchPlanner onOpenOverride={() => setIsOverrideModalOpen(true)} />
        )}
        {activeTab === "benchmark" && <BenchmarkView />}
        {activeTab === "audit" && <AuditLogView logs={auditLogs} />}
      </main>

      <footer className="border-t border-gray-900 bg-gray-950 py-4 text-center text-xs text-gray-500">
        GridShield v0.1.0 — Simulation & Decision-Support System for Microgrids | Developed for Research & Applied AI
      </footer>

      <ManualOverrideModal
        isOpen={isOverrideModalOpen}
        onClose={() => setIsOverrideModalOpen(false)}
        onSuccess={loadData}
      />
    </div>
  );
}

export default App;
