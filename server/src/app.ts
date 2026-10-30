import express, { Express, Request, Response, NextFunction } from "express";
import cors from "cors";
import { config } from "./config/index.js";
import { SimulationService } from "./services/simulationService.js";
import { DispatchService } from "./services/dispatchService.js";
import { createApiRouter } from "./routes/api.js";
import { DatabaseSync } from "node:sqlite";

export function createApp(customDb?: DatabaseSync): Express {
  const app = express();

  app.use(cors({ origin: config.corsOrigin }));
  app.use(express.json());

  const simService = new SimulationService(customDb);
  const dispatchService = new DispatchService(customDb);

  app.use("/api", createApiRouter(simService, dispatchService));

  // Global 404 handler
  app.use((req: Request, res: Response) => {
    res.status(404).json({ error: `Cannot ${req.method} ${req.path}` });
  });

  // Global Error Handler
  app.use((err: any, req: Request, res: Response, next: NextFunction) => {
    console.error("Unhandled API Error:", err);
    res.status(500).json({
      error: "Internal Server Error",
      message: err?.message || String(err),
    });
  });

  return app;
}
