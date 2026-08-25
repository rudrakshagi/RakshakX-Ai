// scripts/test-models.js
// Tests GET /v1/models endpoint

const BASE = process.env.BRIDGE_URL ?? "http://localhost:8787";

async function testModels() {
  console.log(`\n🔍 Testing GET ${BASE}/v1/models ...\n`);

  const res = await fetch(`${BASE}/v1/models`);
  const body = await res.json();

  console.log(`Status: ${res.status}`);
  console.log(`Models returned: ${body.data?.length ?? 0}`);

  if (!body.data || body.data.length === 0) {
    console.error("❌ FAIL: No models returned");
    process.exit(1);
  }

  const allPrefixed = body.data.every((m) => m.id.startsWith("oc/"));
  console.log(`All prefixed with oc/: ${allPrefixed ? "✅" : "❌"}`);

  const hasBigPickle = body.data.some((m) => m.id === "oc/big-pickle");
  console.log(`Includes oc/big-pickle: ${hasBigPickle ? "✅" : "⚠️  not found"}`);

  console.log("\nModel list:");
  body.data.forEach((m) => console.log(`  - ${m.id} (owned_by: ${m.owned_by})`));

  if (allPrefixed && body.data.length > 0) {
    console.log("\n✅ PASS: Models endpoint working correctly\n");
  } else {
    console.error("\n❌ FAIL\n");
    process.exit(1);
  }
}

testModels().catch((err) => {
  console.error("❌ FAIL:", err.message);
  process.exit(1);
});
