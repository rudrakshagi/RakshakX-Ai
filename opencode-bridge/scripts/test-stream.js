// scripts/test-stream.js
// Tests POST /v1/chat/completions (streaming)

const BASE = process.env.BRIDGE_URL ?? "http://localhost:8787";

async function testStream() {
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

  for await (const chunk of res.body) {
    const text = decoder.decode(chunk, { stream: true });
    const lines = text.split("\n").filter((l) => l.startsWith("data: "));

    for (const line of lines) {
      const data = line.slice(6).trim();
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
