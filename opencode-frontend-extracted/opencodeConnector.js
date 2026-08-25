// lib/opencodeConnector.js
//
// Replaces the old `asyncio.create_subprocess_exec("opencode", ...)` /
// CLI-spawn approach entirely. This is a plain HTTP client against
// OpenCode Zen. No `opencode` binary needs to be installed anywhere.

import { Readable } from "node:stream";

// Fields we know are safe to forward as-is to an OpenAI-compatible
// /chat/completions endpoint. Keeping an allowlist (rather than just
// forwarding the whole body) means we don't accidentally leak internal
// fields (like our own `oc/` model id) upstream, and we don't blow up
// on fields a given model doesn't support — those get dropped, not forced.
const FORWARDABLE_CHAT_FIELDS = [
  "messages",
  "stream",
  "temperature",
  "top_p",
  "max_tokens",
  "stop",
  "presence_penalty",
  "frequency_penalty",
  "seed",
  "response_format",
  "tools",
  "tool_choice",
  "n",
  "user",
];

export class OpenCodeConnector {
  /**
   * @param {object} provider - providers/opencode.js shape
   * @param {ModelRegistry} registry - shared registry instance (for id translation)
   * @param {object} [opts]
   * @param {string} [opts.apiKey] - optional; provider is noAuth by default
   * @param {typeof fetch} [opts.fetchImpl]
   */
  constructor(provider, registry, opts = {}) {
    this.provider = provider;
    this.registry = registry;
    this.apiKey = opts.apiKey ?? process.env.OPENCODE_API_KEY ?? null;
    this.fetchImpl = opts.fetchImpl ?? fetch;
  }

  _headers() {
    const headers = {
      "Content-Type": "application/json",
      ...this.provider.transport.headers,
    };
    // Auth is optional on this provider (noAuth: true). Only attach it
    // if the caller actually configured a key — never hard-require it.
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }
    return headers;
  }

  _endpointFor(/* upstreamModelId */) {
    // Today everything on this provider goes through /chat/completions.
    // If you later add models that require /responses (see the
    // gpt-5.6-* family in the wider Zen catalog), branch here based on
    // a capability map rather than a hardcoded model-name check.
    return `${this.provider.transport.baseUrl}/zen/v1/chat/completions`;
  }

  _buildPayload(rawBody, upstreamModelId) {
    const payload = { model: upstreamModelId };
    for (const field of FORWARDABLE_CHAT_FIELDS) {
      if (rawBody[field] !== undefined) payload[field] = rawBody[field];
    }
    return payload;
  }

  /**
   * Non-streaming chat completion. Returns the parsed JSON response.
   * @param {object} rawBody - the incoming OpenAI-compatible request body,
   *   with `model` still in `oc/<id>` (passthrough) form.
   */
  async chat(rawBody) {
    const upstreamModelId = this.registry.toUpstreamId(rawBody.model);
    const payload = this._buildPayload({ ...rawBody, stream: false }, upstreamModelId);

    const res = await this.fetchImpl(this._endpointFor(upstreamModelId), {
      method: "POST",
      headers: this._headers(),
      body: JSON.stringify(payload),
    });

    const text = await res.text();
    if (!res.ok) {
      const err = new Error(`OpenCode Zen ${res.status} ${res.statusText}: ${text}`);
      err.status = res.status;
      err.upstreamBody = text;
      throw err;
    }
    return JSON.parse(text);
  }

  /**
   * Streaming chat completion. Returns a Node Readable stream of raw
   * SSE bytes ("data: {...}\n\n" chunks) exactly as upstream sends them —
   * the caller (route handler) is responsible for piping this to the
   * client response untouched. We do NOT buffer the whole response.
   */
  async chatStream(rawBody) {
    const upstreamModelId = this.registry.toUpstreamId(rawBody.model);
    const payload = this._buildPayload({ ...rawBody, stream: true }, upstreamModelId);

    const res = await this.fetchImpl(this._endpointFor(upstreamModelId), {
      method: "POST",
      headers: this._headers(),
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text();
      const err = new Error(`OpenCode Zen ${res.status} ${res.statusText}: ${text}`);
      err.status = res.status;
      err.upstreamBody = text;
      throw err;
    }

    // node-fetch / undici give us a web ReadableStream in res.body.
    // Convert to a Node stream so it can be piped to an Express response.
    return Readable.fromWeb(res.body);
  }
}

export default OpenCodeConnector;
