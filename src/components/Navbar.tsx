import React from "react";
import { Shield, RefreshCw, AlertTriangle } from "lucide-react";

interface NavbarProps {
  onRefresh: () => void;
  isLoading: boolean;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onRefresh,
  isLoading,
  activeTab,
  setActiveTab,
}) => {
  return (
    <header className="bg-gray-900 border-b border-gray-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight text-white">GridShield</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                  UCC-MPC Active
                </span>
              </div>
              <p className="text-xs text-gray-400">Carbon-Aware Micro-Grid Decision Support</p>
            </div>
          </div>

          <nav className="flex items-center space-x-1 sm:space-x-2">
            {[
              { id: "overview", label: "Operations Overview" },
              { id: "planner", label: "Dispatch Planner" },
              { id: "benchmark", label: "Research Benchmarks" },
              { id: "audit", label: "Audit & Safety Logs" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? "bg-gray-800 text-white border border-gray-700 shadow-sm"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-850"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center space-x-3">
            <div className="hidden lg:flex items-center space-x-2 text-xs text-amber-400/90 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-md">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Simulation Platform — Non-Physical Certified</span>
            </div>

            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="p-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white border border-gray-700 transition"
              title="Refresh telemetry"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin text-emerald-400" : ""}`} />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
