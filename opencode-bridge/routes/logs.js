// routes/logs.js
import { Router } from "express";
import { readFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";

export function buildLogsRouter() {
  const router = Router();
  const logsDir = resolve(process.cwd(), "..", "logs");
  const localLogsDir = resolve(process.cwd(), "logs");

  function getLogPath(filename) {
    const candidates = [
      join(process.cwd(), "logs", filename),
      join(logsDir, filename),
      join(localLogsDir, filename),
      join(process.cwd(), filename),
      resolve(process.cwd(), "..", filename),
      resolve(process.cwd(), "..", "logs", filename),
    ];
    for (const cand of candidates) {
      if (existsSync(cand)) return cand;
    }
    return null;
  }

  function readTailLines(filePath, maxLines = 100) {
    if (!filePath || !existsSync(filePath)) return [];
    try {
      const content = readFileSync(filePath, "utf-8");
      const lines = content.split(/\r?\n/).filter((l) => l.trim().length > 0);
      return lines.slice(-maxLines);
    } catch {
      return [];
    }
  }

  function parseLogLine(line, defaultSource = "system") {
    let level = "INFO";
    let message = line;
    let timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });

    if (line.includes("non-fatal") || line.includes("Tracing client error")) {
      level = "INFO";
    } else if (line.includes("ERROR") || line.includes("error") || line.includes("Exception") || line.includes("failed")) {
      level = "ERROR";
    } else if (line.includes("WARN") || line.includes("warning")) {
      level = "WARN";
    } else if (line.includes("SUCCESS") || line.includes("online") || line.includes("200 OK")) {
      level = "SUCCESS";
    }

    // Try to extract ISO / bracketed timestamp
    const tsMatch = line.match(/^\[?(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}[^\]\s]*|\d{2}:\d{2}:\d{2})\]?/);
    if (tsMatch) {
      timestamp = tsMatch[1];
    }

    return {
      timestamp,
      level,
      source: defaultSource,
      message,
      raw: line,
    };
  }

  // GET /v1/logs?source=all|backend|bridge|frontend&lines=100
  router.get("/v1/logs", (req, res) => {
    const sourceFilter = String(req.query.source || "all").toLowerCase();
    const limit = Math.min(500, Math.max(10, parseInt(req.query.lines || "100", 10)));

    const backendPath = getLogPath("backend.log");
    const bridgePath = getLogPath("bridge.log");
    const frontendPath = getLogPath("frontend.log");
    const rawScanPath = getLogPath(join("rudra-passive", "raw_scan.log"));

    const logs = [];

    if (sourceFilter === "all" || sourceFilter === "backend") {
      const backendLines = readTailLines(backendPath, limit);
      backendLines.forEach((l) => logs.push(parseLogLine(l, "Python Backend")));
    }

    if (sourceFilter === "all" || sourceFilter === "bridge") {
      const bridgeLines = readTailLines(bridgePath, limit);
      bridgeLines.forEach((l) => logs.push(parseLogLine(l, "OpenCode Bridge")));
    }

    if (sourceFilter === "all" || sourceFilter === "frontend") {
      const frontendLines = readTailLines(frontendPath, limit);
      frontendLines.forEach((l) => logs.push(parseLogLine(l, "Frontend Console")));
    }

    if (sourceFilter === "all" || sourceFilter === "scan") {
      const scanLines = readTailLines(rawScanPath, limit);
      scanLines.forEach((l) => logs.push(parseLogLine(l, "Docker Sandbox Target")));
    }

    // Sort by timestamp or slice to limit
    const sorted = logs.slice(-limit);

    res.json({
      ok: true,
      count: sorted.length,
      sources: ["backend", "bridge", "frontend", "scan"],
      logs: sorted,
    });
  });

  return router;
}

export default buildLogsRouter;

