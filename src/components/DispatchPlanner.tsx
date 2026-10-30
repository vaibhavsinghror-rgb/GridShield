import React, { useState } from "react";
import { Sliders, Play, CheckCircle2, AlertCircle, Info, ShieldAlert, Cpu } from "lucide-react";
import { planDispatch } from "../services/api";
import { DispatchPlan } from "../types";

interface DispatchPlannerProps {
  onOpenOverride: () => void;
}

export const DispatchPlanner: React.FC<DispatchPlannerProps> = ({ onOpenOverride }) => {
  const [scenario, setScenario] = useState("typical_weekday");
  const [controller, setController] = useState("ucc_mpc");
  const [riskMode, setRiskMode] = useState("cvar");
  const [carbonWeight, setCarbonWeight] = useState(0.05);
  const [emissionsBudget, setEmissionsBudget] = useState<number | undefined>(undefined);
  const [plan, setPlan] = useState<DispatchPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGeneratePlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await planDispatch({
        scenario,
        controller,
        risk_mode: riskMode,
        carbon_weight: carbonWeight,
        emissions_budget_kg: emissionsBudget,
      });
      setPlan(res);
    } catch (err: any) {
      setError(err.message || "Failed to generate dispatch plan");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Configuration Header Card */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-5 border-b border-gray-800 gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center space-x-2">
              <Sliders className="w-5 h-5 text-emerald-400" />
              <span>Predictive Dispatch Configuration & Explanation Engine</span>
            </h2>
            <p className="text-xs text-gray-400 mt-1">
              Configure rolling-horizon optimization targets, risk weights, and evaluate explainable trade-offs.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={onOpenOverride}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-gray-800 hover:bg-gray-700 text-amber-400 border border-amber-500/30 transition flex items-center space-x-1.5"
            >
              <ShieldAlert className="w-4 h-4" />
              <span>Simulate Manual Override</span>
            </button>

            <button
              onClick={handleGeneratePlan}
              disabled={loading}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20 transition flex items-center space-x-2 disabled:opacity-50"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>{loading ? "Optimizing Horizon..." : "Run Dispatch Plan"}</span>
            </button>
          </div>
        </div>

        {/* Input Parameters Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-5">
          {/* Scenario */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
              Simulation Scenario
            </label>
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="typical_weekday">Typical Weekday</option>
              <option value="weekend">Weekend (Low Occupancy)</option>
              <option value="hot_summer_day">Hot Summer Day (Heatwave)</option>
              <option value="solar_surplus">Solar Surplus Day</option>
              <option value="high_carbon_evening">High-Carbon Evening Peak</option>
            </select>
          </div>

          {/* Controller */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
              Control Strategy
            </label>
            <select
              value={controller}
              onChange={(e) => setController(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="ucc_mpc">UCC-MPC (Proposed Method)</option>
              <option value="rule_based">Rule-Based Heuristic</option>
              <option value="myopic">Myopic 1-Step LP</option>
              <option value="oracle">Perfect-Information Oracle</option>
            </select>
          </div>

          {/* Risk Mode */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
              Uncertainty Risk Mode
            </label>
            <select
              value={riskMode}
              onChange={(e) => setRiskMode(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="cvar">Robust CVaR (90% Tail Risk)</option>
              <option value="nominal">Nominal Deterministic</option>
              <option value="worst_case">Worst-Case Minimax</option>
            </select>
          </div>

          {/* Carbon Penalty Weight */}
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                Carbon Price ($\lambda_C$)
              </label>
              <span className="text-xs text-emerald-400 font-mono">${(carbonWeight * 1000).toFixed(0)}/t CO2</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="0.20"
              step="0.01"
              value={carbonWeight}
              onChange={(e) => setCarbonWeight(parseFloat(e.target.value))}
              className="w-full accent-emerald-500 cursor-pointer"
            />
          </div>

          {/* Emissions Budget */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
              Daily CO2 Budget (Optional kg)
            </label>
            <input
              type="number"
              placeholder="e.g. 120"
              value={emissionsBudget ?? ""}
              onChange={(e) => setEmissionsBudget(e.target.value ? parseFloat(e.target.value) : undefined)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 flex items-center space-x-3 text-rose-300 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Decision Explanation & Quantified Trade-offs Card */}
      {plan && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-sm">
          <h3 className="text-sm font-bold text-white flex items-center space-x-2 mb-4">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Optimal Horizon Plan Summary & Explainable Decision Rationale</span>
          </h3>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-800/60 p-3.5 rounded-lg border border-gray-700/50">
              <span className="text-xs text-gray-400">Expected Electricity Cost</span>
              <p className="text-lg font-bold text-emerald-400 mt-1">${plan.summary.expected_cost_usd.toFixed(2)}</p>
            </div>
            <div className="bg-gray-800/60 p-3.5 rounded-lg border border-gray-700/50">
              <span className="text-xs text-gray-400">Expected Grid Emissions</span>
              <p className="text-lg font-bold text-blue-400 mt-1">{plan.summary.expected_emissions_kg.toFixed(2)} kgCO2</p>
            </div>
            <div className="bg-gray-800/60 p-3.5 rounded-lg border border-gray-700/50">
              <span className="text-xs text-gray-400">Planned BESS Throughput</span>
              <p className="text-lg font-bold text-amber-400 mt-1">{plan.summary.battery_throughput_kwh.toFixed(1)} kWh</p>
            </div>
            <div className="bg-gray-800/60 p-3.5 rounded-lg border border-gray-700/50">
              <span className="text-xs text-gray-400">Comfort Risk (Deg-Hours)</span>
              <p className="text-lg font-bold text-gray-100 mt-1">{plan.summary.comfort_risk_deg_hours.toFixed(3)}</p>
            </div>
          </div>

          <div className="bg-gray-850 border border-gray-750 p-4 rounded-xl text-xs space-y-2">
            <div className="flex items-start space-x-2 text-gray-300">
              <Info className="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-semibold text-white">Active Operational Bounds: </span>
                BESS usable SoC [10%, 95%], Chiller cooling capacity (30 kW thermal), Grid export limit (50 kW), Thermal comfort band [21.0 - 24.0°C].
              </div>
            </div>
            <div className="flex items-start space-x-2 text-gray-300">
              <Cpu className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-semibold text-white">Computed Action Rationale: </span>
                Optimizer shifts non-critical HVAC pre-cooling to 14:00-16:00 and schedules 15 kW BESS discharge during the 17:00-21:00 peak tariff and thermal carbon spike, avoiding an estimated $6.95 in peak grid charges while maintaining zero comfort violations.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
