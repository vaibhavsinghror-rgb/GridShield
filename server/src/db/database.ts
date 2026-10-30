import { DatabaseSync } from "node:sqlite";
import fs from "fs";
import path from "path";
import { config } from "../config/index.js";
import { MIGRATIONS } from "./migrations.js";

let dbInstance: DatabaseSync | null = null;

export function getDatabase(customPath?: string): DatabaseSync {
  if (dbInstance && !customPath) {
    return dbInstance;
  }

  const resolvedPath = customPath || config.dbPath;
  if (resolvedPath !== ":memory:") {
    const dir = path.dirname(resolvedPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  }

  const db = new DatabaseSync(resolvedPath);
  // Enable foreign keys
  db.exec("PRAGMA foreign_keys = ON;");

  // Run migrations
  for (const migrationSql of MIGRATIONS) {
    db.exec(migrationSql);
  }

  // Seed default assets if empty
  const countRow = db.prepare("SELECT COUNT(*) as count FROM assets").get() as { count: number };
  if (countRow.count === 0) {
    seedDefaultAssets(db);
  }

  if (!customPath) {
    dbInstance = db;
  }
  return db;
}

function seedDefaultAssets(db: DatabaseSync): void {
  const assets = [
    { id: "asset-bess-01", name: "Commercial Li-ion BESS", type: "BATTERY", cap: 100.0, unit: "kWh" },
    { id: "asset-solar-01", name: "Rooftop Monocrystalline PV", type: "SOLAR", cap: 40.0, unit: "kW" },
    { id: "asset-hvac-01", name: "Building Central Chiller & Heat Pump", type: "HVAC", cap: 30.0, unit: "kW_thermal" },
    { id: "asset-grid-01", name: "Utility Grid Inter-tie", type: "GRID", cap: 100.0, unit: "kW" },
  ];

  const stmt = db.prepare(`
    INSERT INTO assets (id, name, asset_type, capacity_val, capacity_unit)
    VALUES (?, ?, ?, ?, ?)
  `);

  for (const a of assets) {
    stmt.run(a.id, a.name, a.type, a.cap, a.unit);
  }
}
