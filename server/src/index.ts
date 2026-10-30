import { createApp } from "./app.js";
import { config } from "./config/index.js";

const app = createApp();

app.listen(config.port, () => {
  console.log(`GridShield REST API running at http://localhost:${config.port}`);
  console.log(`Database initialized at: ${config.dbPath}`);
});
