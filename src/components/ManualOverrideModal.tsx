import React, { useState } from "react";
import { X, ShieldAlert, CheckCircle2, AlertCircle } from "lucide-react";
import { submitManualOverride } from "../services/api";

interface ManualOverrideModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const ManualOverrideModal: React.FC<ManualOverrideModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [actor, setActor] = useState("Facility-Operator-01");
  const [coolingKw, setCoolingKw] = useState(15.0);
  const [chargeKw, setChargeKw] = useState(0.0);
  const [dischargeKw, setDischargeKw] = useState(15.0);
  const [reason, setReason] = useState("Pre-cooling and battery peak shaving test for upcoming grid carbon event");
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [loading, setLoading] = useState(false);
  const [resultMsg, setResultMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResultMsg(null);
    setErrorMsg(null);

    const idempotencyKey = `ovr-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

    try {
      const res = await submitManualOverride({
        idempotency_key: idempotencyKey,
        actor,
        hvac_cooling_thermal_kw: coolingKw,
        battery_charge_kw: chargeKw,
        battery_discharge_kw: dischargeKw,
        reason,
        duration_minutes: durationMinutes,
      });

      setResultMsg(`Override successfully registered (ID: ${res.override_id}). Audit record committed.`);
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1500);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit override");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between p-5 border-b border-gray-800 bg-gray-850">
          <div className="flex items-center space-x-2 text-amber-400">
            <ShieldAlert className="w-5 h-5" />
            <h3 className="font-bold text-white text-base">Submit Simulated Manual Dispatch Override</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-white hover:bg-gray-750 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs text-amber-300">
            <strong>Simulation Guardrail:</strong> Overrides apply strictly to the simulated microgrid environment. No real physical relays or switchgear are modified.
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">
              Authorized Actor ID
            </label>
            <input
              type="text"
              required
              value={actor}
              onChange={(e) => setActor(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">
                Cooling (kW)
              </label>
              <input
                type="number"
                min="0"
                max="30"
                step="0.5"
                value={coolingKw}
                onChange={(e) => setCoolingKw(parseFloat(e.target.value) || 0)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">
                Charge (kW)
              </label>
              <input
                type="number"
                min="0"
                max="25"
                step="0.5"
                value={chargeKw}
                onChange={(e) => {
                  const val = parseFloat(e.target.value) || 0;
                  setChargeKw(val);
                  if (val > 0) setDischargeKw(0);
                }}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">
                Discharge (kW)
              </label>
              <input
                type="number"
                min="0"
                max="25"
                step="0.5"
                value={dischargeKw}
                onChange={(e) => {
                  const val = parseFloat(e.target.value) || 0;
                  setDischargeKw(val);
                  if (val > 0) setChargeKw(0);
                }}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">
              Override Duration (Minutes)
            </label>
            <select
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(parseInt(e.target.value, 10))}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
            >
              <option value={15}>15 Minutes (1 Step)</option>
              <option value={30}>30 Minutes</option>
              <option value={60}>60 Minutes (1 Hour)</option>
              <option value={120}>120 Minutes (2 Hours)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">
              Engineering Justification / Reason
            </label>
            <textarea
              required
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
              placeholder="Provide verifiable reason for manual intervention..."
            />
          </div>

          {resultMsg && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-xs text-emerald-300 flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>{resultMsg}</span>
            </div>
          )}

          {errorMsg && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-3 border-t border-gray-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-800 hover:bg-gray-750 text-gray-300 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition disabled:opacity-50"
            >
              {loading ? "Registering..." : "Submit Override"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
