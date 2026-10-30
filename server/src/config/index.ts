import path from "path";
import dotenv from "dotenv";

dotenv.config();

export const config = {
  port: parseInt(process.env.PORT || "4000", 10),
  dbPath: process.env.DB_PATH || path.resolve(process.cwd(), "gridshield.sqlite"),
  corsOrigin: process.env.CORS_ORIGIN || "*",
  projectRoot: path.resolve(process.cwd(), ".."),
  pythonExe: process.env.PYTHON_EXE || path.resolve(process.cwd(), "../.venv/Scripts/python.exe"),
};
