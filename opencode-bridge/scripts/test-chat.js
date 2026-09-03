// scripts/test-chat.js
// Tests POST /v1/chat/completions (non-streaming)

const BASE = process.env.BRIDGE_URL ?? "http://localhost:8787";

async function testChat() {
  // First, get a model to use
  const modelsRes = await fetch(`${BASE}/v1/models`);
  const modelsBody = await modelsRes.json();
  // Prefer verified-working free models first (verified live 2026-09-03).
  const PREFERRED = [
    "oc/nemotron-3.5-lightning-free",
    "oc/muse-spark-1.3-contributor-free",
    "oc/laguna-s-2.1-free",
    "oc/muse-spark-1.2-contributor-free",
  ];
  const ids = new Set((modelsBody.data ?? []).map((m) => m.id));
  const model =
    PREFERRED.find((id) => ids.has(id)) ??
    modelsBody.data?.find((m) => m.id.includes("-free"))?.id ??
    modelsBody.data?.[0]?.id;

  if (!model) {
    console.error("❌ No models available");
    process.exit(1);
  }

  console.log(`\n💬 Testing non-streaming chat with model: ${model}\n`);

  const res = await fetch(`${BASE}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      messages: [{ role: "user", content: "Hello, reply in one sentence." }],
      stream: false,
    }),
  });

  const body = await res.json();
  console.log(`Status: ${res.status}`);

  if (!res.ok) {
    console.error("❌ FAIL:", body.error?.message ?? JSON.stringify(body));
    process.exit(1);
  }

  const reply = body.choices?.[0]?.message?.content;
  console.log(`Reply: ${reply}`);
  console.log(`Model used: ${body.model ?? "unknown"}`);

  if (reply && reply.length > 0) {
    console.log("\n✅ PASS: Non-streaming chat working correctly\n");
  } else {
    console.error("\n❌ FAIL: Empty reply\n");
    process.exit(1);
  }
}

testChat().catch((err) => {
  console.error("❌ FAIL:", err.message);
  process.exit(1);
});
