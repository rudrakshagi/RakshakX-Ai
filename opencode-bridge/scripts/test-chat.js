// scripts/test-chat.js
// Tests POST /v1/chat/completions (non-streaming)

const BASE = process.env.BRIDGE_URL ?? "http://localhost:8787";

async function testChat() {
  // First, get a model to use
  const modelsRes = await fetch(`${BASE}/v1/models`);
  const modelsBody = await modelsRes.json();
  const freeModel = modelsBody.data?.find(
    (m) => m.id === "oc/big-pickle" || m.id.includes("-free")
  );
  const model = freeModel?.id ?? modelsBody.data?.[0]?.id;

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
