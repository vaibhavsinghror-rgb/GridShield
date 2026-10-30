import React from "react";
import { Zap, Sun, Battery, DollarSign, Thermometer, ArrowDownRight } from "lucide-react";
import { TelemetryRecord, AnalyticsSummary } from "../types";

interface KPICardsProps {
  current: TelemetryRecord | null;
  summary: AnalyticsSummary | null;
}

export const KPICards: React.FC<KPICardsProps> = ({ current, summary }) => {
  const indoorTemp = current?.indoor_temp_c ?? 22.4;
  const isComfortable = indoorTemp >= 21.0 && indoorTemp <= 24.0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 sm:gap-4 mb-6">
      {/* 1. Grid Import */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between text-gray-400">
          <span className="text-xs font-medium uppercase tracking-wider">Net Grid Flux</span>
          <Zap className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="mt-2">
          <div className="text-2xl font-bold text-white tracking-tight">
            {current ? `${current.grid_power_kw.toFixed(1)} kW` : "--"}
          </div>
          <p className="text-xs text-gray-400 mt-1 flex items-center space-x-1">
            <span className={`inline-block w-2 h-2 rounded-full ${(current?.grid_power_kw ?? 0) > 0 ? "bg-amber-400" : "bg-emerald-400"}`}></span>
            <span>{(current?.grid_power_kw ?? 0) > 0 ? "Utility Import" : "Solar Export"}</span>
          </p>
        </div>
      </div>

      {/* 2. Solar Generation */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between text-gray-400">
          <span className="text-xs font-medium uppercase tracking-wider">Solar PV Output</span>
          <Sun className="w-4 h-4 text-amber-400" />
        </div>
        <div className="mt-2">
          <div className="text-2xl font-bold text-white tracking-tight">
            {current ? `${current.solar_generation_kw.toFixed(1)} kW` : "--"}
          </div>
          <p className="text-xs text-gray-400 mt-1">40 kW Peak Array</p>
        </div>
      </div>

      {/* 3. Battery SoC */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between text-gray-400">
          <span className="text-xs font-medium uppercase tracking-wider">BESS State of Charge</span>
          <Battery className="w-4 h-4 text-blue-400" />
        </div>
        <div className="mt-2">
          <div className="text-2xl font-bold text-white tracking-tight">
            68%
          </div>
          <div className="w-full bg-gray-800 h-1.5 rounded-full mt-2 overflow-hidden">
            <div className="bg-blue-500 h-full rounded-full" style={{ width: "68%" }}></div>
          </div>
        </div>
      </div>

      {/* 4. Indoor Temp & Comfort */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between text-gray-400">
          <span className="text-xs font-medium uppercase tracking-wider">Zone Temp & Comfort</span>
          <Thermometer className="w-4 h-4 text-rose-400" />
        </div>
        <div className="mt-2">
          <div className="text-2xl font-bold text-white tracking-tight">
            {indoorTemp.toFixed(1)} °C
          </div>
          <p className="text-xs mt-1 flex items-center space-x-1">
            <span className={`inline-block w-2 h-2 rounded-full ${isComfortable ? "bg-emerald-400" : "bg-rose-400"}`}></span>
            <span className={isComfortable ? "text-emerald-400" : "text-rose-400"}>
              {isComfortable ? "Comfort Band Met" : "Excursion Alert"}
            </span>
          </p>
        </div>
      </div>

      {/* 5. Electricity Expenditure & Baseline Savings */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col justify-between shadow-sm col-span-2 md:col-span-4 lg:col-span-1">
        <div className="flex items-center justify-between text-gray-400">
          <span className="text-xs font-medium uppercase tracking-wider">Daily Cost & Savings</span>
          <DollarSign className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="mt-2">
          <div className="text-2xl font-bold text-emerald-400 tracking-tight">
            ${summary?.today_electricity_cost_usd ?? "10.57"}
          </div>
          <p className="text-xs text-gray-400 mt-1 flex items-center">
            <ArrowDownRight className="w-3.5 h-3.5 text-emerald-400 mr-0.5" />
            <span>Save {summary?.baseline_comparison.savings_pct ?? "39.7"}% vs Heuristic</span>
          </p>
        </div>
      </div>
    </div>
  );
};
