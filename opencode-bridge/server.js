// server.js
import "dotenv/config";
import express from "express";
import cors from "cors";

import { openCodeProvider } from "./providers/opencode.js";
import { ModelRegistry } from "./lib/modelRegistry.js";
import { OpenCodeConnector } from "./lib/opencodeConnector.js";
import { buildModelsRouter } from "./routes/models.js";
import { buildChatRouter } from "./routes/chat.js";
import { buildAgentsRouter } from "./routes/agents.js";
import { buildLogsRouter } from "./routes/logs.js";

const PORT = process.env.PORT ?? 8787;
const CACHE_TTL_MS = Number(process.env.MODEL_CACHE_TTL_MS ?? 10 * 60 * 1000);

const app = express();
app.use(cors());
app.use(express.json({ limit: "10mb" }));

// --- wiring -----------------------------------------------------------
const registry = new ModelRegistry(openCodeProvider, { ttlMs: CACHE_TTL_MS });
const connector = new OpenCodeConnector(openCodeProvider, registry);

app.use(buildModelsRouter(registry));
app.use(buildChatRouter(registry, connector));
app.use(buildAgentsRouter({ backendBase: process.env.RAKSHAK_BACKEND ?? "http://127.0.0.1:8080" }));
app.use(buildLogsRouter());

app.get("/healthz", (req, res) => res.json({ ok: true, provider: openCodeProvider.id }));

// --- startup ------------------------------------------------------------
async function start() {
  try {
    const models = await registry.getModels();
    console.log(`[startup] loaded ${models.length} models from ${openCodeProvider.modelsFetcher.url}`);
  } catch (err) {
    console.warn(`[startup] initial model fetch failed (${err.message}); will retry in background`);
  }

  registry.startAutoRefresh(CACHE_TTL_MS);

  // Bind 0.0.0.0 explicitly: bare app.listen() may resolve to ::1 only,
  // which breaks the Vite proxy that targets 127.0.0.1:8787.
  const HOST = process.env.HOST ?? "0.0.0.0";
  app.listen(PORT, HOST, () => {
    console.log(`[opencode-bridge] listening on http://${HOST}:${PORT}`);
    console.log(`  GET  /v1/models`);
    console.log(`  POST /v1/chat/completions`);
  });
}

start();
