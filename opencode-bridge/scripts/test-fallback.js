// scripts/test-fallback.js
// Dependency-free tests for OpenCodeConnector fallback (stub fetchImpl style).
// Run: node scripts/test-fallback.js  (from opencode-bridge/)

import { OpenCodeConnector, DEFAULT_FALLBACK_MODEL } from "../lib/opencodeConnector.js";

let failures = 0;
let passes = 0;
function check(name, cond, detail = "") {
  if (cond) {
    passes += 1;
    console.log(`PASS: ${name}`);
  } else {
    failures += 1;
    console.log(`FAIL: ${name}${detail ? ` — ${detail}` : ""}`);
  }
}

const PRIMARY = "oc/primary-model";
const FALLBACK = "oc/fallback-model";

const fakeProvider = { transport: { baseUrl: "http://x", headers: {} } };
const fakeRegistry = {
  toUpstreamId: (m) => String(m).replace(/^oc\//, ""),
  getModelMeta: async () => null,
};

function okCompletion(modelLabel) {
  return {
    id: `chatcmpl-${modelLabel}`,
    object: "chat.completion",
    created: 123,
    model: modelLabel,
    choices: [{ index: 0, message: { role: "assistant", content: `hello from ${modelLabel}` }, finish_reason: "stop" }],
  };
}

function okFetch(bodyObj) {
  return { ok: true, status: 200, statusText: "OK", text: async () => JSON.stringify(bodyObj) };
}
function errFetch(status, bodyText, statusText = "Error") {
  return { ok: false, status, statusText, text: async () => bodyText };
}

// Build a connector whose fetchImpl replays a scripted sequence.
// Each entry: { ok, status, body } or { throw: Error }.
// Records upstream payload model per call.
function buildScriptedConnector(script) {
  const calls = [];
  const fetchImpl = async (_url, opts = {}) => {
    let payloadModel = null;
    try {
      payloadModel = JSON.parse(opts.body ?? "{}").model ?? null;
    } catch { /* keep null */ }
    const idx = calls.length;
    calls.push({ payloadModel });
    const step = script[Math.min(idx, script.length - 1)];
    if (step?.throw) throw step.throw;
    if (step?.ok) return okFetch(step.body);
    return errFetch(step.status, step.bodyText ?? "", step.statusText);
  };
  const connector = new OpenCodeConnector(fakeProvider, fakeRegistry, { fetchImpl });
  return { connector, calls };
}

function baseBody(model = PRIMARY) {
  return { model, messages: [{ role: "user", content: "hi" }], stream: false };
}

// 1. success first-try (fallbackUsed false, 1 call)
{
  const { connector, calls } = buildScriptedConnector([{ ok: true, body: okCompletion("primary-model") }]);
  const r = await connector.chatWithFallback(baseBody(), { fallbackModel: FALLBACK });
  check("success first-try: fallbackUsed false", r.fallbackUsed === false, JSON.stringify(r.fallbackUsed));
  check("success first-try: 1 upstream call", calls.length === 1, `calls=${calls.length}`);
  check("success first-try: completion content", r.completion?.choices?.[0]?.message?.content?.includes("hello") === true);
}

// 2. 500 then success (fallbackUsed true, 2 calls, 2nd model == fallback upstream)
{
  const { connector, calls } = buildScriptedConnector([
    { ok: false, status: 500, bodyText: "internal error", statusText: "Internal Server Error" },
    { ok: true, body: okCompletion("fallback-model") },
  ]);
  const r = await connector.chatWithFallback(baseBody(), { fallbackModel: FALLBACK });
  check("500→fallback: fallbackUsed true", r.fallbackUsed === true);
  check("500→fallback: fallbackModel echoed", r.fallbackModel === FALLBACK, `got ${r.fallbackModel}`);
  check("500→fallback: 2 upstream calls", calls.length === 2, `calls=${calls.length}`);
  check("500→fallback: 2nd call model == fallback upstream", calls[1]?.payloadModel === "fallback-model", `got ${calls[1]?.payloadModel}`);
}

// 3. 429 then success
{
  const { connector, calls } = buildScriptedConnector([
    { ok: false, status: 429, bodyText: "rate limited", statusText: "Too Many Requests" },
    { ok: true, body: okCompletion("fallback-model") },
  ]);
  const r = await connector.chatWithFallback(baseBody(), { fallbackModel: FALLBACK });
  check("429→fallback: fallbackUsed true + 2 calls", r.fallbackUsed === true && calls.length === 2, `used=${r.fallbackUsed} calls=${calls.length}`);
}

// 4. 400 model_not_found → fallback
{
  const { connector, calls } = buildScriptedConnector([
    { ok: false, status: 400, bodyText: '{"error":"model_not_found"}', statusText: "Bad Request" },
    { ok: true, body: okCompletion("fallback-model") },
  ]);
  const r = await connector.chatWithFallback(baseBody(), { fallbackModel: FALLBACK });
  check("400 model_not_found → fallback", r.fallbackUsed === true && calls.length === 2, `used=${r.fallbackUsed} calls=${calls.length}`);
}

// 5. 400 invalid_request_args → NO fallback (throws, 1 call)
{
  const { connector, calls } = buildScriptedConnector([
    { ok: false, status: 400, bodyText: '{"error":"invalid_request_args: missing field"}', statusText: "Bad Request" },
  ]);
  let threw = null;
  try {
    await connector.chatWithFallback(baseBody(), { fallbackModel: FALLBACK });
  } catch (e) { threw = e; }
  check("400 invalid_request_args → throws (no fallback)", threw?.status === 400, `got status=${threw?.status}`);
  check("400 invalid_request_args → 1 call only", calls.length === 1, `calls=${calls.length}`);
}

// 6. 401 → NO fallback
{
  const { connector, calls } = buildScriptedConnector([
    { ok: false, status: 401, bodyText: "unauthorized", statusText: "Unauthorized" },
  ]);
  let threw = null;
  try {
    await connector.chatWithFallback(baseBody(), { fallbackModel: FALLBACK });
  } catch (e) { threw = e; }
  check("401 → throws (no fallback)", threw?.status === 401, `got status=${threw?.status}`);
  check("401 → 1 call only", calls.length === 1, `calls=${calls.length}`);
}

// 7. network throw (no status) → fallback
{
  const netErr = new Error("socket hang up");
  const { connector, calls } = buildScriptedConnector([
    { throw: netErr },
    { ok: true, body: okCompletion("fallback-model") },
  ]);
  const r = await connector.chatWithFallback(baseBody(), { fallbackModel: FALLBACK });
  check("network throw → fallback", r.fallbackUsed === true && calls.length === 2, `used=${r.fallbackUsed} calls=${calls.length}`);
}

// 8. already-on-fallback failing worthy → throws (no infinite loop)
{
  const { connector, calls } = buildScriptedConnector([
    { ok: false, status: 500, bodyText: "boom", statusText: "Internal Server Error" },
  ]);
  let threw = null;
  try {
    await connector.chatWithFallback(baseBody(FALLBACK), { fallbackModel: FALLBACK });
  } catch (e) { threw = e; }
  check("already-on-fallback 500 → throws", threw?.status === 500, `got status=${threw?.status}`);
  check("already-on-fallback → exactly 1 call (no loop)", calls.length === 1, `calls=${calls.length}`);
}

// 9. isFallbackWorthy unit matrix
{
  const T = (err) => OpenCodeConnector.isFallbackWorthy(err);
  const mk = (status, msg) => { const e = new Error(msg); e.status = status; e.upstreamBody = msg; return e; };
  check("worthy: 429", T(mk(429, "rate limited")) === true);
  check("worthy: 500", T(mk(500, "err")) === true);
  check("worthy: 502", T(mk(502, "bad gateway")) === true);
  check("worthy: 503", T(mk(503, "unavailable")) === true);
  check("worthy: network (no status)", T(new Error("socket hang up")) === true);
  check("worthy: 400 model_not_found", T(mk(400, "model_not_found")) === true);
  check("worthy: 400 'Model Not Found' (case-insensitive)", T(mk(400, "Model Not Found")) === true);
  check("worthy: 400 unknown model", T(mk(400, "unknown model xyz")) === true);
  check("worthy: 400 unsupported model", T(mk(400, "unsupported model")) === true);
  check("worthy: 400 does not exist", T(mk(400, "model does not exist")) === true);
  check("worthy: 400 not available", T(mk(400, "model not available on tier")) === true);
  check("worthy: 400 unknown parameter", T(mk(400, "unknown parameter: messages")) === true);
  check("worthy: 400 unsupported parameter", T(mk(400, "unsupported parameter")) === true);
  check("worthy: 400 muse-spark marker", T(mk(400, "muse-spark needs responses api")) === true);
  check("not worthy: 400 invalid_request_args", T(mk(400, "invalid_request_args: bad args")) === false);
  check("not worthy: 400 generic validation", T(mk(400, "missing required field messages")) === false);
  check("not worthy: 401", T(mk(401, "unauthorized")) === false);
  check("not worthy: 403", T(mk(403, "forbidden")) === false);
  check("not worthy: 404", T(mk(404, "not found")) === false);
  check("not worthy: null/non-object", T(null) === false && T("x") === false);
}

// 10. DEFAULT_FALLBACK_MODEL sane
{
  check("DEFAULT_FALLBACK_MODEL is oc/… string", typeof DEFAULT_FALLBACK_MODEL === "string" && DEFAULT_FALLBACK_MODEL.startsWith("oc/"), `got ${DEFAULT_FALLBACK_MODEL}`);
}

if (failures > 0) {
  console.log(`\n${failures} case(s) FAILED, ${passes} passed`);
  process.exit(1);
} else {
  console.log(`\nAll fallback cases PASSED (${passes} checks)`);
}
