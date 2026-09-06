// routes/agents.js
import { Router } from "express";

class AgentManager {
  constructor() {
    this.agents = new Map();
  }

  getAgents() {
    return Array.from(this.agents.values());
  }

  updateAgent(id, updates) {
    const existing = this.agents.get(id);
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const logs = existing ? [...(existing.logs || [])] : [];
    if (updates.action) {
      const logEntry = `[${timestamp}] ${updates.action}`;
      if (logs[logs.length - 1] !== logEntry) {
        logs.push(logEntry);
        if (logs.length > 10) logs.shift();
      }
    }
    if (updates.currentTool) {
      const toolLog = `[${timestamp}] Executing tool: ${updates.currentTool}`;
      if (logs[logs.length - 1] !== toolLog) {
        logs.push(toolLog);
        if (logs.length > 10) logs.shift();
      }
    }

    if (existing) {
      this.agents.set(id, {
        ...existing,
        ...updates,
        logs: updates.logs || logs,
        updatedAt: new Date().toISOString(),
      });
    } else {
      this.agents.set(id, {
        id,
        name: updates.name || id,
        type: updates.type || "Specialist Subagent",
        status: updates.status || "running",
        action: updates.action || "Executing security analysis",
        currentTool: updates.currentTool,
        progress: updates.progress || 10,
        logs: updates.logs || logs,
        updatedAt: new Date().toISOString(),
      });
    }
  }

  triggerActivity(promptText) {
    // No-op: fake agents are disabled. Only real spawned agents via /v1/agents/spawn or backend scans are tracked.
  }

  fallbackAgents() {
    return this.getAgents();
  }
}

export const agentManager = new AgentManager();

/**
 * Real proxy over the RakshakX viewer backend. Falls back to mock data
 * only when the backend fetch fails (marked source:'fallback').
 * @param {object} [opts]
 * @param {string} [opts.backendBase]
 * @param {typeof fetch} [opts.fetchImpl]
 */
export function buildAgentsRouter(opts = {}) {
  const router = Router();
  const backendBase = (opts.backendBase ?? process.env.RAKSHAK_BACKEND ?? "http://127.0.0.1:8080").replace(/\/$/, "");
  const fetchImpl = opts.fetchImpl ?? fetch;

  async function backendFetch(path, init) {
    const res = await fetchImpl(`${backendBase}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
    const text = await res.text();
    if (!res.ok) {
      const err = new Error(`backend ${res.status}: ${text.slice(0, 500)}`);
      err.status = res.status;
      throw err;
    }
    try {
      return JSON.parse(text);
    } catch {
      return { raw: text };
    }
  }

  // GET /v1/agents -> live backend /api/agents, fallback to local agents on failure
  router.get("/v1/agents", async (req, res) => {
    try {
      const data = await backendFetch("/api/agents");
      let list = [];
      if (Array.isArray(data)) {
        list = data;
      } else if (data && typeof data === "object" && data.names) {
        const names = data.names || {};
        const statuses = data.statuses || {};
        const meta = data.metadata || {};
        list = Object.keys(names).map((aid) => ({
          id: aid,
          name: names[aid] || aid,
          type: aid === "root_01" || aid === "agent-root" || aid.includes("root") ? "Root Orchestrator" : "Specialist Subagent",
          status: (statuses[aid] || "completed").toLowerCase(),
          action: meta[aid]?.task || meta[aid]?.action || "Executing security task",
          currentTool: meta[aid]?.current_tool,
          progress: meta[aid]?.progress ?? (statuses[aid] === "completed" ? 100 : 75),
          logs: meta[aid]?.logs || [],
        }));
      } else if (Array.isArray(data?.data)) {
        list = data.data;
      }
      res.json({ object: "list", data: list, count: list.length, source: "live" });
    } catch (err) {
      console.warn(`[GET /v1/agents] backend unreachable (${err.message}); serving fallback`);
      const fallbackList = agentManager.fallbackAgents();
      res.json({ object: "list", data: fallbackList, count: fallbackList.length, source: "fallback" });
    }
  });

  // POST /v1/agents/spawn {name,task,target,mode} -> POST backend /api/scan
  router.post("/v1/agents/spawn", async (req, res) => {
    const { name, task, target, mode } = req.body ?? {};
    if (!task) {
      return res.status(400).json({ error: { message: "`task` is required", type: "invalid_request" } });
    }
    const agentId = `agent-${Date.now().toString(36)}`;
    agentManager.updateAgent(agentId, {
      name: name || "Autonomous Security Agent",
      type: "Specialist Subagent",
      status: "running",
      action: task,
      currentTool: "initializing",
      progress: 15,
    });
    try {
      const data = await backendFetch("/api/scan", {
        method: "POST",
        body: JSON.stringify({
          target: target ?? "example.com",
          mode: mode ?? "blackbox",
          prompt: `spawn:${name ? `[${name}] ` : ""}${task}`,
        }),
      });
      res.json({ ok: true, source: "live", data, agentId });
    } catch (err) {
      console.warn("[POST /v1/agents/spawn] backend unreachable, saved to local agent state");
      res.json({ ok: true, source: "local", agentId });
    }
  });

  // POST /v1/agents/message {target_agent_id|instruction} -> POST /api/steer
  router.post("/v1/agents/message", async (req, res) => {
    const { instruction, target_agent_id } = req.body ?? {};
    if (!instruction) {
      return res.status(400).json({ error: { message: "`instruction` is required", type: "invalid_request" } });
    }
    try {
      const data = await backendFetch("/api/steer", {
        method: "POST",
        body: JSON.stringify({ instruction, target_agent_id }),
      });
      res.json({ ok: true, source: "live", data });
    } catch (err) {
      console.error("[POST /v1/agents/message]", err);
      res.status(502).json({ error: { message: err.message, type: "upstream_error" } });
    }
  });

  // POST /v1/agents/trigger -> kept for compat (simulated local updates)
  router.post("/v1/agents/trigger", (req, res) => {
    const { prompt } = req.body || {};
    agentManager.triggerActivity(prompt || "sample execution");
    res.json({ ok: true, data: agentManager.getAgents() });
  });

  return router;
}

export default buildAgentsRouter;
