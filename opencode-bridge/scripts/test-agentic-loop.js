// scripts/test-agentic-loop.js
// E2E/unit coverage for the bridge agentic chat loop (dependency-free).
// Exercises the REAL ToolExecutor + RAKSHAK_TOOLS with a stub fetchImpl.
// Run: node scripts/test-agentic-loop.js  (from opencode-bridge/)

import { RAKSHAK_TOOLS, DESTRUCTIVE_TOOLS } from "../lib/rakshakTools.js";
import { ToolExecutor } from "../lib/toolExecutor.js";

let failures = 0;

function check(name, cond, detail = "") {
  if (cond) {
    console.log(`PASS: ${name}`);
  } else {
    failures += 1;
    console.log(`FAIL: ${name}${detail ? ` — ${detail}` : ""}`);
  }
}

// --- stub backend -----------------------------------------------------------
const calls = [];
const agentsPayload = { names: { root_01: "root" }, statuses: { root_01: "running" }, metadata: {} };

function stubFetch(url, opts = {}) {
  const method = (opts.method ?? "GET").toUpperCase();
  let body;
  try {
    body = opts.body ? JSON.parse(opts.body) : undefined;
  } catch {
    body = opts.body;
  }
  calls.push({ url, method, body });
  const path = String(url).replace(/^https?:\/\/[^/]+/, "");
  const jsonResponse = (obj) => ({
    ok: true,
    status: 200,
    text: async () => JSON.stringify(obj),
  });
  if (path === "/api/agents" && method === "GET") return Promise.resolve(jsonResponse(agentsPayload));
  if (path === "/api/scan" && method === "POST") {
    return Promise.resolve(jsonResponse({ success: true, scan_id: "scan-test123", target: body?.target ?? null }));
  }
  if (path === "/api/steer" && method === "POST") {
    return Promise.resolve(jsonResponse({ success: true, delivered: true }));
  }
  // Fallback: generic ok
  return Promise.resolve(jsonResponse({ ok: true }));
}

const executor = new ToolExecutor({ backendBase: "http://127.0.0.1:8080", fetchImpl: stubFetch });

// (a) 23 tools, valid OpenAI function-tool shape
{
  const okCount = Array.isArray(RAKSHAK_TOOLS) && RAKSHAK_TOOLS.length === 23;
  check("(a) RAKSHAK_TOOLS has 23 entries", okCount, `got ${RAKSHAK_TOOLS?.length}`);
  const names = new Set();
  let shapeOk = true;
  let shapeDetail = "";
  for (const t of RAKSHAK_TOOLS ?? []) {
    const f = t?.function;
    if (t?.type !== "function" || typeof f?.name !== "string" || typeof f?.description !== "string" || typeof f?.parameters !== "object") {
      shapeOk = false;
      shapeDetail = `bad shape for ${JSON.stringify(t)?.slice(0, 120)}`;
      break;
    }
    if (f.parameters?.type !== "object") {
      shapeOk = false;
      shapeDetail = `parameters.type !== object for ${f.name}`;
      break;
    }
    if (names.has(f.name)) {
      shapeOk = false;
      shapeDetail = `duplicate tool name ${f.name}`;
      break;
    }
    names.add(f.name);
  }
  check("(a) all tools have valid {type:function, function:{name,description,parameters}} shape", shapeOk, shapeDetail);
  for (const required of ["rakshak_start_scan", "agent_list", "agent_steer", "agent_spawn"]) {
    check(`(a) tool present: ${required}`, names.has(required), "missing");
  }
}

// (b) agent_list ok with stub backend {names,statuses,metadata}
{
  const out = await executor.executeOne({ name: "agent_list", args: {} });
  let parsed = null;
  try {
    parsed = JSON.parse(out.resultText);
  } catch { /* keep null */ }
  const ok = out.ok === true && parsed && typeof parsed.names === "object" && typeof parsed.statuses === "object" && typeof parsed.metadata === "object";
  check("(b) agent_list returns {names,statuses,metadata} via stub backend", ok, `got ${out.resultText.slice(0, 200)}`);
}

// (c) unknown tool error
{
  const out = await executor.executeOne({ name: "does_not_exist_tool", args: {} });
  check("(c) unknown tool returns ok:false with 'unknown tool' error", out.ok === false && /unknown tool/.test(out.error ?? out.resultText ?? ""), `got ${JSON.stringify(out).slice(0, 200)}`);
}

// (d) rakshak_start_scan POSTs to /api/scan with target
{
  calls.length = 0;
  const out = await executor.executeOne({ name: "rakshak_start_scan", args: { target: "example.com", mode: "blackbox" } });
  const hit = calls.find((c) => c.url.endsWith("/api/scan") && c.method === "POST");
  check("(d) rakshak_start_scan POSTs to /api/scan", Boolean(hit), `calls: ${JSON.stringify(calls).slice(0, 200)}`);
  check("(d) rakshak_start_scan forwards target", hit?.body?.target === "example.com", `body: ${JSON.stringify(hit?.body)}`);
  check("(d) rakshak_start_scan ok", out.ok === true, out.resultText.slice(0, 200));
}

// (e) agent_steer POSTs /api/steer
{
  calls.length = 0;
  const out = await executor.executeOne({ name: "agent_steer", args: { instruction: "focus on jwt" } });
  const hit = calls.find((c) => c.url.endsWith("/api/steer") && c.method === "POST");
  check("(e) agent_steer POSTs to /api/steer", Boolean(hit), `calls: ${JSON.stringify(calls).slice(0, 200)}`);
  check("(e) agent_steer forwards instruction", hit?.body?.instruction === "focus on jwt", `body: ${JSON.stringify(hit?.body)}`);
  check("(e) agent_steer ok", out.ok === true, out.resultText.slice(0, 200));
}

// (f) DESTRUCTIVE list contains agent_spawn + start_scan
{
  check("(f) DESTRUCTIVE_TOOLS contains agent_spawn", DESTRUCTIVE_TOOLS.includes("agent_spawn"), `got ${JSON.stringify(DESTRUCTIVE_TOOLS)}`);
  check("(f) DESTRUCTIVE_TOOLS contains rakshak_start_scan", DESTRUCTIVE_TOOLS.includes("rakshak_start_scan"), `got ${JSON.stringify(DESTRUCTIVE_TOOLS)}`);
}

if (failures > 0) {
  console.log(`\n${failures} case(s) FAILED`);
  process.exit(1);
} else {
  console.log("\nAll agentic-loop cases PASSED");
}
