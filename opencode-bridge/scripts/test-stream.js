// scripts/test-stream.js
// Tests POST /v1/chat/completions (streaming)

const BASE = process.env.BRIDGE_URL ?? "http://localhost:8787";

async function testStream() {
  // First, get a model to use — prefer verified-working free models.
  const modelsRes = await fetch(`${BASE}/v1/models`);
  const modelsBody = await modelsRes.json();
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

  console.log(`\n🌊 Testing streaming chat with model: ${model}\n`);

  const res = await fetch(`${BASE}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      messages: [{ role: "user", content: "Count from 1 to 5, one number per line." }],
      stream: true,
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    console.error(`❌ FAIL: ${res.status} ${errText}`);
    process.exit(1);
  }

  console.log(`Status: ${res.status}`);
  console.log(`Content-Type: ${res.headers.get("content-type")}`);
  console.log("\nStreaming tokens:\n---");

  const decoder = new TextDecoder();
  let fullContent = "";
  let chunkCount = 0;

  let buffer = "";
  for await (const chunk of res.body) {
    buffer += decoder.decode(chunk, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data: ")) continue;
      const data = trimmed.slice(6);
      if (data === "[DONE]") {
        console.log("\n---\n[DONE] received");
        continue;
      }
      try {
        const parsed = JSON.parse(data);
        const delta = parsed.choices?.[0]?.delta?.content ?? "";
        if (delta) {
          process.stdout.write(delta);
          fullContent += delta;
          chunkCount++;
        }
      } catch {
        // skip non-JSON lines
      }
    }
  }

  console.log(`\n\nChunks received: ${chunkCount}`);
  console.log(`Full content length: ${fullContent.length}`);

  if (chunkCount > 1 && fullContent.length > 0) {
    console.log("\n✅ PASS: Streaming chat working correctly (multiple chunks received)\n");
  } else if (fullContent.length > 0) {
    console.log("\n⚠️  PARTIAL PASS: Got content but in a single chunk\n");
  } else {
    console.error("\n❌ FAIL: No content received\n");
    process.exit(1);
  }
}

testStream().catch((err) => {
  console.error("❌ FAIL:", err.message);
  process.exit(1);
});
