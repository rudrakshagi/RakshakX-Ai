// scripts/e2e-test.js
// Full end-to-end test suite for opencode-bridge
// Covers: models list, non-streaming chat, streaming chat, error handling, model switch

const BASE = process.env.BRIDGE_URL ?? "http://localhost:8787";
const results = [];

const originalFetch = globalThis.fetch;
globalThis.fetch = async function fetchWithRetry(url, options = {}, maxRetries = 3, delayMs = 3000) {
  // If streaming request (POST to completions with stream: true), we should only retry if the initial request fails
  // Before consuming the body. That's automatically handled by this loop since we check res.ok.
  for (let i = 0; i < maxRetries; i++) {
    try {
      const res = await originalFetch(url, options);
      if (res.ok || res.status === 404) {
        return res;
      }
      console.log(`⚠️ Request to ${url} returned status ${res.status}. Retry ${i+1}/${maxRetries}...`);
    } catch (err) {
      console.log(`⚠️ Request to ${url} failed with error: ${err.message}. Retry ${i+1}/${maxRetries}...`);
    }
    if (i < maxRetries - 1) {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
  return originalFetch(url, options);
};

function log(msg) {
  console.log(msg);
}

function record(testName, passed, details) {
  results.push({ testName, passed, details });
  const icon = passed ? "✅" : "❌";
  log(`${icon} ${testName}: ${details}\n`);
}

// ─── Test A: GET /v1/models ───────────────────────────────────────────
async function testA_Models() {
  log("═══════════════════════════════════════════════════");
  log("TEST A: GET /v1/models");
  log("═══════════════════════════════════════════════════\n");

  const res = await fetch(`${BASE}/v1/models`);
  const body = await res.json();

  log(`Status: ${res.status}`);
  log(`Models returned: ${body.data?.length ?? 0}`);

  if (!body.data || body.data.length === 0) {
    record("A: Models list", false, "No models returned");
    return null;
  }

  const allPrefixed = body.data.every((m) => m.id.startsWith("oc/"));
  log(`All prefixed with oc/: ${allPrefixed}`);

  const hasBigPickle = body.data.some((m) => m.id === "oc/big-pickle");
  log(`Includes oc/big-pickle: ${hasBigPickle}`);

  log("\nFull model list:");
  body.data.forEach((m) => log(`  • ${m.id}`));
  log("");

  const passed = allPrefixed && body.data.length > 0;
  record(
    "A: Models list",
    passed,
    `${body.data.length} models, all oc/ prefixed: ${allPrefixed}, big-pickle: ${hasBigPickle}`
  );

  return body.data;
}

// ─── Test B: Non-streaming chat ──────────────────────────────────────
async function testB_NonStreamingChat(models) {
  log("═══════════════════════════════════════════════════");
  log("TEST B: Non-streaming chat");
  log("═══════════════════════════════════════════════════\n");

  // Use nemotron for test B to spread load and avoid rate limiting
  const model =
    models.find((m) => m.id === "oc/nemotron-3.5-lightning-free")?.id ??
    models.find((m) => m.id === "oc/big-pickle")?.id ??
    models.find((m) => m.id.includes("-free"))?.id ??
    models[0]?.id;

  log(`Using model: ${model}`);

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
  log(`Status: ${res.status}`);

  if (!res.ok) {
    record("B: Non-streaming chat", false, `HTTP ${res.status}: ${body.error?.message}`);
    return;
  }

  const reply = body.choices?.[0]?.message?.content;
  log(`Reply: ${reply}`);
  log(`Model in response: ${body.model ?? "not specified"}`);

  const passed = reply && reply.length > 0;
  record("B: Non-streaming chat", passed, passed ? `Got reply (${reply.length} chars)` : "Empty reply");
}

// ─── Test C: Streaming chat ──────────────────────────────────────────
async function testC_StreamingChat(models) {
  log("═══════════════════════════════════════════════════");
  log("TEST C: Streaming chat");
  log("═══════════════════════════════════════════════════\n");

  // Use nemotron-3.5-lightning-free for streaming test as it is verified working and supports streaming
  const model =
    models.find((m) => m.id === "oc/nemotron-3.5-lightning-free")?.id ??
    models.find((m) => m.id === "oc/big-pickle")?.id ??
    models.find((m) => m.id.includes("-free"))?.id ??
    models[0]?.id;

  log(`Using model: ${model}`);

  const res = await fetch(`${BASE}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      messages: [{ role: "user", content: "Write a short paragraph about the color blue. Make it at least 3 sentences long." }],
      stream: true,
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    record("C: Streaming chat", false, `HTTP ${res.status}: ${errText}`);
    return;
  }

  log(`Content-Type: ${res.headers.get("content-type")}`);
  log("\nStreaming output:\n---");

  const decoder = new TextDecoder();
  let fullContent = "";
  let sseEventCount = 0;
  let contentDeltaCount = 0;
  let tcpChunkCount = 0;
  let gotDone = false;

  for await (const chunk of res.body) {
    tcpChunkCount++;
    const text = decoder.decode(chunk, { stream: true });
    const lines = text.split("\n").filter((l) => l.startsWith("data: "));

    for (const line of lines) {
      sseEventCount++;
      const data = line.slice(6).trim();
      if (data === "[DONE]") {
        gotDone = true;
        continue;
      }
      try {
        const parsed = JSON.parse(data);
        const delta = parsed.choices?.[0]?.delta?.content || parsed.choices?.[0]?.delta?.reasoning || "";
        if (delta) {
          process.stdout.write(delta);
          fullContent += delta;
          contentDeltaCount++;
        }
      } catch {
        // skip
      }
    }
  }

  log(`\n---\nTCP chunks: ${tcpChunkCount}, SSE events: ${sseEventCount}, Content deltas: ${contentDeltaCount}`);
  log(`Content length: ${fullContent.length}, [DONE]: ${gotDone}`);

  // Streaming is confirmed working if:
  // 1. We got text/event-stream content-type
  // 2. We received SSE data events
  // 3. We got the [DONE] signal
  // 4. We got actual content
  const isStreaming = res.headers.get("content-type")?.includes("text/event-stream");
  const passed = isStreaming && gotDone && fullContent.length > 0 && sseEventCount >= 2;
  record(
    "C: Streaming chat",
    passed,
    passed
      ? `${sseEventCount} SSE events, ${contentDeltaCount} content deltas, ${tcpChunkCount} TCP chunks, [DONE] received`
      : `isStreaming: ${isStreaming}, gotDone: ${gotDone}, content: ${fullContent.length}, events: ${sseEventCount}`
  );
}

// ─── Test D: Error handling ──────────────────────────────────────────
async function testD_ErrorHandling() {
  log("═══════════════════════════════════════════════════");
  log("TEST D: Error handling (invalid model)");
  log("═══════════════════════════════════════════════════\n");

  const res = await fetch(`${BASE}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "oc/this-model-does-not-exist-12345",
      messages: [{ role: "user", content: "Hello" }],
      stream: false,
    }),
  });

  const body = await res.json();
  log(`Status: ${res.status}`);
  log(`Error response: ${JSON.stringify(body, null, 2)}`);

  const passed = res.status >= 400 && body.error?.message;
  record(
    "D: Error handling",
    passed,
    passed
      ? `Got clean ${res.status} with message: "${body.error.message}"`
      : `Unexpected response: ${res.status}`
  );
}

// ─── Test E: Model switch ────────────────────────────────────────────
async function testE_ModelSwitch(models) {
  log("═══════════════════════════════════════════════════");
  log("TEST E: Model switch mid-session");
  log("═══════════════════════════════════════════════════\n");

  if (models.length < 2) {
    record("E: Model switch", false, "Less than 2 models available — cannot test switch");
    return;
  }

  // Use known-working free models for reliability
  const PREFERRED_MODELS = [
    "oc/nemotron-3.5-lightning-free",
    "oc/hy3-free",
    "oc/big-pickle",
    "oc/nemotron-3-ultra-free",
    "oc/laguna-s-2.1-free",
    "oc/muse-spark-1.2-contributor-free",
  ];
  
  const available = PREFERRED_MODELS.filter((id) =>
    models.some((m) => m.id === id)
  );
  
  let model1, model2;
  if (available.length >= 2) {
    model1 = available[0];
    model2 = available[1];
  } else {
    // Fallback to any two models
    model1 = available[0] ?? models[0].id;
    model2 = models.find((m) => m.id !== model1)?.id ?? models[1].id;
  }

  log(`Model 1: ${model1}`);
  log(`Model 2: ${model2}`);

  // First request with model1
  log(`\nSending request with ${model1}...`);
  const res1 = await fetch(`${BASE}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: model1,
      messages: [{ role: "user", content: "Say the word 'alpha'. Only respond with that single word." }],
      stream: false,
    }),
  });

  const body1 = await res1.json();
  const reply1 = body1.choices?.[0]?.message?.content ?? "(no reply)";
  log(`Reply from ${model1}: ${reply1}`);
  log(`Response model field: ${body1.model ?? "not specified"}`);

  // Second request with model2
  log(`\nSending request with ${model2}...`);
  const res2 = await fetch(`${BASE}/v1/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: model2,
      messages: [
        { role: "user", content: "Say the word 'alpha'. Only respond with that single word." },
        { role: "assistant", content: reply1 },
        { role: "user", content: "Say the word 'beta'. Only respond with that single word." },
      ],
      stream: false,
    }),
  });

  const body2 = await res2.json();
  const reply2 = body2.choices?.[0]?.message?.content ?? "(no reply)";
  log(`Reply from ${model2}: ${reply2}`);
  log(`Response model field: ${body2.model ?? "not specified"}`);

  const passed = res1.ok && res2.ok && reply1.length > 0 && reply2.length > 0;
  record(
    "E: Model switch",
    passed,
    passed
      ? `Both models responded. ${model1} -> "${reply1.slice(0, 50)}", ${model2} -> "${reply2.slice(0, 50)}"`
      : "One or both models failed to respond"
  );
}

// ─── Main ────────────────────────────────────────────────────────────
async function main() {
  log("\n╔═══════════════════════════════════════════════════╗");
  log("║   OPENCODE-BRIDGE FULL E2E TEST SUITE            ║");
  log("╚═══════════════════════════════════════════════════╝\n");
  log(`Bridge URL: ${BASE}\n`);

  // Healthcheck first
  try {
    const hRes = await fetch(`${BASE}/healthz`);
    const hBody = await hRes.json();
    log(`Healthcheck: ${JSON.stringify(hBody)}\n`);
  } catch (err) {
    log(`❌ Bridge not reachable at ${BASE}: ${err.message}`);
    log("Make sure the bridge is running (npm start) before running tests.");
    process.exit(1);
  }

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const models = await testA_Models();
  if (!models) {
    log("⛔ Cannot continue without models. Exiting.\n");
    printSummary();
    process.exit(1);
  }

  log("Sleeping 2s before Test B...");
  await sleep(2000);
  await testB_NonStreamingChat(models);
  
  log("Sleeping 5s before Test C...");
  await sleep(5000);
  await testC_StreamingChat(models);
  
  log("Sleeping 5s before Test D...");
  await sleep(5000);
  await testD_ErrorHandling();
  
  log("Sleeping 5s before Test E...");
  await sleep(5000);
  await testE_ModelSwitch(models);

  printSummary();
}

function printSummary() {
  log("\n╔═══════════════════════════════════════════════════╗");
  log("║   E2E TEST RESULTS SUMMARY                       ║");
  log("╚═══════════════════════════════════════════════════╝\n");

  for (const r of results) {
    const icon = r.passed ? "✅" : "❌";
    log(`  ${icon} ${r.testName}`);
    log(`     ${r.details}\n`);
  }

  const passed = results.filter((r) => r.passed).length;
  const total = results.length;
  log(`\nResult: ${passed}/${total} tests passed\n`);

  if (passed < total) process.exit(1);
}

main().catch((err) => {
  console.error("❌ Fatal error:", err.message);
  process.exit(1);
});
