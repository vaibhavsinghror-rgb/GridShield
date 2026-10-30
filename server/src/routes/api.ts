import { Router, Request, Response } from "express";
import fs from "fs";
import path from "path";
import { SimulationService } from "../services/simulationService.js";
import { DispatchService } from "../services/dispatchService.js";
import {
  DispatchPlanRequestSchema,
  DispatchOverrideRequestSchema,
  PaginationQuerySchema,
} from "../schemas/index.js";

export function createApiRouter(
  simService: SimulationService,
  dispatchService: DispatchService
): Router {
  const router = Router();

  // 1. Health
  router.get("/health", (req: Request, res: Response) => {
    res.json({
      status: "HEALTHY",
      platform: "GridShield Decision Support Platform",
      engine: "Deterministic Simulation & UCC-MPC Optimizer",
      version: "0.1.0",
      timestamp: new Date().toISOString(),
    });
  });

  // 2. Telemetry
  router.get("/telemetry/current", (req: Request, res: Response) => {
    const current = simService.getCurrentTelemetry();
    if (!current) {
      return res.status(404).json({ error: "No telemetry records found" });
    }
    res.json(current);
  });

  router.get("/telemetry/history", (req: Request, res: Response) => {
    const parse = PaginationQuerySchema.safeParse(req.query);
    if (!parse.success) {
      return res.status(400).json({ error: parse.error.format() });
    }
    const { limit, offset } = parse.data;
    const history = simService.getTelemetryHistory(limit, offset);
    res.json({
      total: history.length,
      limit,
      offset,
      data: history,
    });
  });

  // 3. Assets
  router.get("/assets", (req: Request, res: Response) => {
    const assets = simService.getAssets();
    res.json(assets);
  });

  // 4. Tariffs & Carbon
  router.get("/tariffs", (req: Request, res: Response) => {
    const tariffs = simService.getTariffObservations();
    res.json(tariffs);
  });

  router.get("/carbon", (req: Request, res: Response) => {
    const carbon = simService.getCarbonObservations();
    res.json(carbon);
  });

  // 5. Dispatch Current & Plan
  router.get("/dispatch/current", (req: Request, res: Response) => {
    const currentDispatch = dispatchService.getCurrentDispatch();
    res.json(currentDispatch);
  });

  router.post("/dispatch/plan", (req: Request, res: Response) => {
    const parse = DispatchPlanRequestSchema.safeParse(req.body);
    if (!parse.success) {
      return res.status(400).json({ error: parse.error.format() });
    }
    const plan = dispatchService.planDispatch(parse.data);
    res.json(plan);
  });

  // 6. Dispatch Manual Override
  router.post("/dispatch/override", (req: Request, res: Response) => {
    const parse = DispatchOverrideRequestSchema.safeParse(req.body);
    if (!parse.success) {
      return res.status(400).json({ error: parse.error.format() });
    }
    try {
      const result = dispatchService.applyManualOverride(parse.data);
      res.status(result.idempotent_replay ? 200 : 201).json(result);
    } catch (err: any) {
      res.status(500).json({ error: err.message || "Failed to process override" });
    }
  });

  // 7. Analytics Summary
  router.get("/analytics/summary", (req: Request, res: Response) => {
    const summary = simService.getAnalyticsSummary();
    res.json(summary);
  });

  // 8. Audit Logs
  router.get("/audit-logs", (req: Request, res: Response) => {
    const parse = PaginationQuerySchema.safeParse(req.query);
    if (!parse.success) {
      return res.status(400).json({ error: parse.error.format() });
    }
    const { limit, offset } = parse.data;
    const logs = dispatchService.getAuditLogs(limit, offset);
    res.json({
      limit,
      offset,
      data: logs,
    });
  });

  // 9. Experiments Summary (reads generated benchmark files if available)
  router.get("/experiments", (req: Request, res: Response) => {
    const benchmarkPath = path.resolve(process.cwd(), "../experiments/results/baseline/benchmark_summary.json");
    if (fs.existsSync(benchmarkPath)) {
      try {
        const data = JSON.parse(fs.readFileSync(benchmarkPath, "utf-8"));
        return res.json({ source: "experiments/results/baseline", count: data.length, data });
      } catch (e) {
        // Fallback
      }
    }
    res.json({ source: "mock", data: [] });
  });

  return router;
}
