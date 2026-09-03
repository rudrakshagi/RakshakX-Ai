// scripts/test-agents.js
// Tests GET /v1/agents endpoint and agent cards data structure

const BASE = process.env.BRIDGE_URL ?? "http://localhost:8787";

async function testAgents() {
  console.log(`\n🔍 Testing GET ${BASE}/v1/agents ...\n`);

  const res = await fetch(`${BASE}/v1/agents`);
  const body = await res.json();

  console.log(`Status: ${res.status}`);
  console.log(`Agents returned: ${body.data?.length ?? 0}`);

  if (!body.data || body.data.length === 0) {
    console.error("❌ FAIL: No agents returned");
    process.exit(1);
  }

  console.log("\nActive Agents List:");
  body.data.forEach((agent) => {
    console.log(`  - [${agent.status.toUpperCase()}] ${agent.name} (${agent.type})`);
    console.log(`    Action: ${agent.action}`);
    console.log(`    Tool: ${agent.currentTool || 'N/A'} | Progress: ${agent.progress}%`);
  });

  const hasRoot = body.data.some((a) => a.id === "root-orchestrator");
  console.log(`\nIncludes Root Orchestrator: ${hasRoot ? "✅" : "❌"}`);

  if (res.ok && body.data.length > 0 && hasRoot) {
    console.log("\n✅ PASS: Agents endpoint working correctly!\n");
  } else {
    console.error("\n❌ FAIL\n");
    process.exit(1);
  }
}

testAgents().catch((err) => {
  console.error("❌ FAIL:", err.message);
  process.exit(1);
});
