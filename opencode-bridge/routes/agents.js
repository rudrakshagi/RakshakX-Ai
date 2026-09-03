// routes/agents.js
import { Router } from "express";

class AgentManager {
  constructor() {
    this.agents = new Map([
      [
        "root-orchestrator",
        {
          id: "root-orchestrator",
          name: "Root Orchestrator",
          type: "Root Agent",
          status: "running",
          action: "Orchestrating security audit & delegating specialist tasks",
          currentTool: "create_agent",
          progress: 75,
          logs: ["Analyzing prompt requirements", "Spawning specialist subagents", "Awaiting subagent reports"],
          updatedAt: new Date().toISOString(),
        },
      ],
      [
        "recon-specialist",
        {
          id: "recon-specialist",
          name: "Reconnaissance Subagent",
          type: "Specialist Subagent",
          status: "executing_tool",
          action: "Scanning active services and mapping web application attack surface",
          currentTool: "nmap_service_scan",
          progress: 85,
          logs: ["Port 80/tcp OPEN (HTTP)", "Port 443/tcp OPEN (HTTPS)", "Header inspection completed"],
          updatedAt: new Date().toISOString(),
        },
      ],
      [
        "sqli-specialist",
        {
          id: "sqli-specialist",
          name: "SQL Injection Specialist",
          type: "Specialist Subagent",
          status: "thinking",
          action: "Testing parameters for boolean-based blind SQL injection",
          currentTool: "sql_payload_injector",
          progress: 60,
          logs: ["Testing GET param 'id'", "Analyzing response time delta", "Payload verified"],
          updatedAt: new Date().toISOString(),
        },
      ],
      [
        "jwt-auth-agent",
        {
          id: "jwt-auth-agent",
          name: "JWT Auth Specialist",
          type: "Specialist Subagent",
          status: "running",
          action: "Auditing JWT header algorithms (none-alg, HS256 key confusion)",
          currentTool: "jwt_token_fuzzer",
          progress: 90,
          logs: ["Captured Bearer token", "Testing 'none' algorithm bypass", "Testing weak HMAC secret"],
          updatedAt: new Date().toISOString(),
        },
      ],
      [
        "report-synthesizer",
        {
          id: "report-synthesizer",
          name: "Report Synthesizer Subagent",
          type: "Synthesis Agent",
          status: "waiting",
          action: "Awaiting final vulnerability findings to construct executive summary",
          currentTool: "agent_finish",
          progress: 40,
          logs: ["Initialized report structure", "Listening on subagent mailbox"],
          updatedAt: new Date().toISOString(),
        },
      ],
    ]);
  }

  getAgents() {
    return Array.from(this.agents.values());
  }

  updateAgent(id, updates) {
    const existing = this.agents.get(id);
    if (existing) {
      this.agents.set(id, {
        ...existing,
        ...updates,
        updatedAt: new Date().toISOString(),
      });
    }
  }

  triggerActivity(promptText) {
    const text = (promptText || "").toLowerCase();
    
    if (text.includes("sql") || text.includes("inject")) {
      this.updateAgent("sqli-specialist", {
        status: "executing_tool",
        action: `Executing SQL injection audit for query: "${promptText.slice(0, 30)}..."`,
        progress: Math.min(95, (this.agents.get("sqli-specialist").progress + 15) % 100),
      });
    } else if (text.includes("jwt") || text.includes("token") || text.includes("auth")) {
      this.updateAgent("jwt-auth-agent", {
        status: "executing_tool",
        action: `Analyzing JWT token security for query: "${promptText.slice(0, 30)}..."`,
        progress: Math.min(95, (this.agents.get("jwt-auth-agent").progress + 20) % 100),
      });
    } else {
      this.getAgents().forEach(agent => {
        const nextProgress = Math.min(100, agent.progress + Math.floor(Math.random() * 10) + 5);
        this.updateAgent(agent.id, {
          progress: nextProgress >= 100 ? 100 : nextProgress,
          status: nextProgress >= 100 ? "completed" : (nextProgress % 2 === 0 ? "executing_tool" : "thinking"),
        });
      });
    }
  }
}

export const agentManager = new AgentManager();

export function buildAgentsRouter() {
  const router = Router();

  // GET /v1/agents -> List all active agents & status cards data
  router.get("/v1/agents", (req, res) => {
    res.json({
      object: "list",
      data: agentManager.getAgents(),
      count: agentManager.agents.size,
    });
  });

  // POST /v1/agents/trigger -> Trigger simulated agent updates
  router.post("/v1/agents/trigger", (req, res) => {
    const { prompt } = req.body || {};
    agentManager.triggerActivity(prompt || "sample execution");
    res.json({ ok: true, data: agentManager.getAgents() });
  });

  return router;
}

export default buildAgentsRouter;

