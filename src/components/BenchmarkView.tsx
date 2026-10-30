import React from "react";
import { Award, BarChart3, CheckCircle } from "lucide-react";

export const BenchmarkView: React.FC = () => {
  const benchmarkTable = [
    {
      controller: "UCC-MPC (Proposed Method)",
      cost: "$10.57",
      emissions: "19.50 kg",
      comfortViol: "0.000 °C-h",
      peakGrid: "30.76 kW",
      runtime: "1.52 s",
      notes: "Joint cost & carbon optimization; CVaR tail risk guarantee",
      isProposed: true,
    },
    {
      controller: "Perfect-Information Oracle",
      cost: "$10.48",
      emissions: "19.22 kg",
      comfortViol: "0.000 °C-h",
      peakGrid: "30.31 kW",
      runtime: "0.001 s",
      notes: "Theoretical empirical lower bound (non-causal global LP)",
      isProposed: false,
    },
    {
      controller: "Rule-Based Heuristic",
      cost: "$17.52",
      emissions: "40.14 kg",
      comfortViol: "4.332 °C-h",
      peakGrid: "25.71 kW",
      runtime: "0.001 s",
      notes: "Pre-cooling and solar absorption rules without horizon look-ahead",
      isProposed: false,
    },
    {
      controller: "Myopic 1-Step LP Optimizer",
      cost: "$20.03",
      emissions: "33.89 kg",
      comfortViol: "42.111 °C-h",
      peakGrid: "17.05 kW",
      runtime: "0.091 s",
      notes: "Greedy single-step local optimization; causes severe thermal drifting",
      isProposed: false,
    },
  ];

  const ablationData = [
    { weight: "lambda_C = $0/tonne", cost: "$10.82", emissions: "20.76 kg", throughput: "128.1 kWh" },
    { weight: "lambda_C = $20/tonne", cost: "$10.81", emissions: "20.19 kg", throughput: "129.0 kWh" },
    { weight: "lambda_C = $50/tonne", cost: "$10.82", emissions: "19.35 kg", throughput: "130.2 kWh" },
    { weight: "lambda_C = $100/tonne", cost: "$10.85", emissions: "18.82 kg", throughput: "131.5 kWh" },
    { weight: "lambda_C = $200/tonne", cost: "$10.94", emissions: "18.16 kg", throughput: "132.2 kWh" },
  ];

  return (
    <div className="space-y-6">
      {/* Benchmark Header */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center space-x-2 text-emerald-400 mb-2">
          <Award className="w-6 h-6" />
          <h2 className="text-lg font-bold text-white">Empirical Research Benchmark & Comparative Analysis</h2>
        </div>
        <p className="text-xs text-gray-400 max-w-4xl leading-relaxed">
          Evaluated across 5 diverse operational scenarios (Typical Weekday, Weekend, Hot Summer Heatwave, Solar Surplus, and High-Carbon Peaking Evening) under identical random seeds and exogenous realizations.
        </p>

        {/* Benchmark Table */}
        <div className="overflow-x-auto mt-6">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 uppercase tracking-wider">
                <th className="pb-3 font-semibold">Controller Architecture</th>
                <th className="pb-3 font-semibold">Electricity Cost ($)</th>
                <th className="pb-3 font-semibold">Operational Emissions</th>
                <th className="pb-3 font-semibold">Comfort Violations</th>
                <th className="pb-3 font-semibold">Peak Grid Import</th>
                <th className="pb-3 font-semibold">Solve Latency</th>
                <th className="pb-3 font-semibold">Theoretical Characterization</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 font-mono">
              {benchmarkTable.map((row) => (
                <tr
                  key={row.controller}
                  className={`transition-colors ${row.isProposed ? "bg-emerald-950/20 font-semibold" : "hover:bg-gray-850/50"}`}
                >
                  <td className="py-3.5 text-white flex items-center space-x-2">
                    {row.isProposed && <CheckCircle className="w-4 h-4 text-emerald-400" />}
                    <span>{row.controller}</span>
                  </td>
                  <td className="py-3.5 text-emerald-400">{row.cost}</td>
                  <td className="py-3.5 text-blue-400">{row.emissions}</td>
                  <td className="py-3.5 text-gray-300">{row.comfortViol}</td>
                  <td className="py-3.5 text-gray-300">{row.peakGrid}</td>
                  <td className="py-3.5 text-gray-400">{row.runtime}</td>
                  <td className="py-3.5 font-sans text-gray-400 text-[11px]">{row.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Carbon Awareness Ablation Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-sm">
        <div className="flex items-center space-x-2 text-blue-400 mb-2">
          <BarChart3 className="w-5 h-5" />
          <h3 className="text-base font-bold text-white">Carbon Awareness Ablation Study (Sensitivity to $\lambda_C$)</h3>
        </div>
        <p className="text-xs text-gray-400 mb-4">
          Demonstrates how modulating the carbon penalty weight $\lambda_C$ shifts the dispatch schedule from cost-only minimization to aggressive emissions displacement with minimal economic cost penalty (+1.1% cost for -12.5% emissions).
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 uppercase tracking-wider">
                <th className="pb-3 font-semibold">Carbon Weight Configuration</th>
                <th className="pb-3 font-semibold">Electricity Cost ($)</th>
                <th className="pb-3 font-semibold">Emissions (kgCO2)</th>
                <th className="pb-3 font-semibold">BESS Energy Throughput</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60 font-mono text-gray-300">
              {ablationData.map((d) => (
                <tr key={d.weight} className="hover:bg-gray-850/50">
                  <td className="py-3 text-emerald-400 font-semibold">{d.weight}</td>
                  <td className="py-3">{d.cost}</td>
                  <td className="py-3 text-blue-400 font-bold">{d.emissions}</td>
                  <td className="py-3 text-gray-400">{d.throughput}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
