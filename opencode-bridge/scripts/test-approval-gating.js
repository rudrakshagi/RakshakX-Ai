// scripts/test-approval-gating.js
// Unit-test for the REAL approval decision (lib/approval.js, dependency-free).
// Run: node scripts/test-approval-gating.js  (from opencode-bridge/)

import { approvalKey, resolveApproval } from "../lib/approval.js";

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

const DESTRUCTIVE = "rakshak_start_scan"; // in DESTRUCTIVE_TOOLS
const SAFE = "agent_list"; // NOT in DESTRUCTIVE_TOOLS
const noopWarn = () => {};

// 1. auto + destructive (no decision) => execute
{
  const r = resolveApproval({ mode: "auto", decisions: {}, callId: "call_1", name: DESTRUCTIVE, args: { target: "example.com" }, warn: noopWarn });
  check("auto + destructive no-decision => execute", r.action === "execute", `got ${r.action}`);
  check("auto mode echoed back", r.mode === "auto", `got ${r.mode}`);
}

// 2. manual + safe => execute (no gating)
{
  const r = resolveApproval({ mode: "manual", decisions: {}, callId: "call_2", name: SAFE, args: {}, warn: noopWarn });
  check("manual + safe tool => execute", r.action === "execute", `got ${r.action}`);
}

// 3. manual + destructive, no decision => pend
{
  const r = resolveApproval({ mode: "manual", decisions: {}, deniedKeys: new Set(), callId: "call_3", name: DESTRUCTIVE, args: { target: "example.com" }, warn: noopWarn });
  check("manual + destructive no-decision => pend", r.action === "pend", `got ${r.action}`);
}

// 4. manual + destructive, approve => execute
{
  const r = resolveApproval({ mode: "manual", decisions: { call_4: "approve" }, deniedKeys: new Set(), callId: "call_4", name: DESTRUCTIVE, args: { target: "example.com" }, warn: noopWarn });
  check("manual + destructive approve => execute", r.action === "execute", `got ${r.action}`);
}

// 5. deny => deny + sticky re-issue (new callId, same args) => deny without decision
{
  const deniedKeys = new Set();
  const args = { target: "example.com", mode: "blackbox" };
  const d = resolveApproval({ mode: "manual", decisions: { call_5: "deny" }, deniedKeys, callId: "call_5", name: DESTRUCTIVE, args, warn: noopWarn });
  check("manual + destructive deny => deny", d.action === "deny", `got ${d.action}`);
  check("deny remembers sticky key", deniedKeys.has(d.key), `keys: ${[...deniedKeys]}`);
  const re = resolveApproval({ mode: "manual", decisions: {}, deniedKeys, callId: "call_6", name: DESTRUCTIVE, args: { ...args }, warn: noopWarn });
  check("sticky re-issue (new callId, same args) => deny without decision", re.action === "deny", `got ${re.action}`);
  // Different args must NOT hit the sticky deny.
  const other = resolveApproval({ mode: "manual", decisions: {}, deniedKeys, callId: "call_7", name: DESTRUCTIVE, args: { target: "other.com" }, warn: noopWarn });
  check("different args => pend (not sticky-denied)", other.action === "pend", `got ${other.action}`);
}

// 6. approve clears sticky deny
{
  const deniedKeys = new Set();
  const args = { target: "example.com" };
  resolveApproval({ mode: "manual", decisions: { c1: "deny" }, deniedKeys, callId: "c1", name: DESTRUCTIVE, args, warn: noopWarn });
  check("sticky set after deny (setup)", deniedKeys.size === 1, `size=${deniedKeys.size}`);
  const a = resolveApproval({ mode: "manual", decisions: { c2: "approve" }, deniedKeys, callId: "c2", name: DESTRUCTIVE, args, warn: noopWarn });
  check("approve on sticky key => execute", a.action === "execute", `got ${a.action}`);
  check("approve clears sticky key", !deniedKeys.has(a.key), `keys: ${[...deniedKeys]}`);
  const after = resolveApproval({ mode: "manual", decisions: {}, deniedKeys, callId: "c3", name: DESTRUCTIVE, args, warn: noopWarn });
  check("after approve-clears, no-decision => pend (not deny)", after.action === "pend", `got ${after.action}`);
}

// 7. unknown mode => execute + warn called once + mode coerced to auto
{
  let warns = 0;
  const r = resolveApproval({ mode: "weird", decisions: {}, callId: "c8", name: DESTRUCTIVE, args: {}, warn: () => { warns += 1; } });
  check("unknown mode => execute (fail-open)", r.action === "execute", `got ${r.action}`);
  check("unknown mode coerced to auto", r.mode === "auto", `got ${r.mode}`);
  check("unknown mode warns exactly once", warns === 1, `warns=${warns}`);
}

// 7b. missing mode defaults to auto => execute, no warn
{
  let warns = 0;
  const r = resolveApproval({ decisions: {}, callId: "c9", name: DESTRUCTIVE, args: {}, warn: () => { warns += 1; } });
  check("missing mode defaults to auto => execute", r.action === "execute" && r.mode === "auto", `got ${r.action}/${r.mode}`);
  check("missing mode does not warn", warns === 0, `warns=${warns}`);
}

// 8. key stability (arg order-insensitive)
{
  const k1 = approvalKey(DESTRUCTIVE, { a: 1, b: 2 });
  const k2 = approvalKey(DESTRUCTIVE, { b: 2, a: 1 });
  check("approvalKey order-insensitive (flat)", k1 === k2, `${k1} vs ${k2}`);
  const n1 = approvalKey(DESTRUCTIVE, { x: { p: 1, q: 2 }, y: [3, 2, 1] });
  const n2 = approvalKey(DESTRUCTIVE, { y: [3, 2, 1], x: { q: 2, p: 1 } });
  check("approvalKey order-insensitive (nested)", n1 === n2, `${n1} vs ${n2}`);
  const k3 = approvalKey(DESTRUCTIVE, { a: 1, b: 3 });
  check("approvalKey differs on different args", k1 !== k3, `${k1} vs ${k3}`);
  const k4 = approvalKey(SAFE, { a: 1, b: 2 });
  check("approvalKey differs on different tool name", k1 !== k4, `${k1} vs ${k4}`);
  // Array order IS significant (only object keys are sorted).
  const a1 = approvalKey(DESTRUCTIVE, { y: [1, 2] });
  const a2 = approvalKey(DESTRUCTIVE, { y: [2, 1] });
  check("approvalKey array order significant", a1 !== a2, `${a1} vs ${a2}`);
}

if (failures > 0) {
  console.log(`\n${failures} case(s) FAILED, ${passes} passed`);
  process.exit(1);
} else {
  console.log(`\nAll approval-gating cases PASSED (${passes} checks)`);
}
