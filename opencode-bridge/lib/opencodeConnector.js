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

  _endpointFor(upstreamModelId, targetFormat) {
    if (this._isResponsesTarget(upstreamModelId, targetFormat)) {
      return `${this.provider.transport.baseUrl}/zen/v1/responses`;
    }
    return `${this.provider.transport.baseUrl}/zen/v1/chat/completions`;
  }

  _isResponsesTarget(upstreamModelId, targetFormat) {
    return targetFormat === "openai-responses" || String(upstreamModelId).includes("muse-spark");
  }

  // --- Chat Completions <-> Responses translation -----------------------
  // Muse Spark models live behind the Responses API, which rejects the
  // Chat Completions `messages` field ("unknown parameter `messages`").
  // The bridge accepts Chat Completions from clients and translates both
  // directions so callers never need to care which upstream API a model
  // uses.

  /** Translate chat-style tools to Responses function-tool shape. */
  _translateToolsForResponses(tools) {
    if (!Array.isArray(tools)) return undefined;
    const out = [];
    for (const t of tools) {
      if (t?.type === "function" && t.function?.name) {
        const fn = { type: "function", name: t.function.name };
        if (t.function.description !== undefined) fn.description = t.function.description;
        if (t.function.parameters !== undefined) fn.parameters = t.function.parameters;
        if (t.function.strict !== undefined) fn.strict = t.function.strict;
        out.push(fn);
      }
      // Non-function tool types have no Responses equivalent — drop them
      // rather than letting upstream 400 the whole request.
    }
    return out.length > 0 ? out : undefined;
  }

  /** Translate chat tool_choice to Responses shape. */
  _translateToolChoiceForResponses(toolChoice) {
    if (toolChoice === undefined) return undefined;
    if (typeof toolChoice === "string") return toolChoice; // auto | none | required
    if (toolChoice?.type === "function" && toolChoice.function?.name) {
      return { type: "function", name: toolChoice.function.name };
    }
    return undefined;
  }

  _buildResponsesPayload(rawBody, upstreamModelId) {
    const payload = { model: upstreamModelId };
    // Responses takes `input`, which accepts the same message array shape.
    if (rawBody.messages !== undefined) payload.input = rawBody.messages;
    if (rawBody.stream !== undefined) payload.stream = rawBody.stream;
    for (const field of ["temperature", "top_p", "user"]) {
      if (rawBody[field] !== undefined) payload[field] = rawBody[field];
    }
    if (rawBody.max_tokens !== undefined) payload.max_output_tokens = rawBody.max_tokens;
    if (rawBody.max_output_tokens !== undefined) payload.max_output_tokens = rawBody.max_output_tokens;
    const tools = this._translateToolsForResponses(rawBody.tools);
    if (tools !== undefined) payload.tools = tools;
    const toolChoice = this._translateToolChoiceForResponses(rawBody.tool_choice);
    if (toolChoice !== undefined) payload.tool_choice = toolChoice;
    return payload;
  }

  _buildPayload(rawBody, upstreamModelId, targetFormat) {
    if (this._isResponsesTarget(upstreamModelId, targetFormat)) {
      return this._buildResponsesPayload(rawBody, upstreamModelId);
    }
    const payload = { model: upstreamModelId };
    for (const field of FORWARDABLE_CHAT_FIELDS) {
      if (rawBody[field] !== undefined) payload[field] = rawBody[field];
    }
    return payload;
  }

  /** Extract assistant text + tool calls from a Responses API response object. */
  _extractResponsesContent(response) {
    let text = "";
    const toolCalls = [];
    for (const item of response?.output ?? []) {
      if (item?.type === "message" && Array.isArray(item.content)) {
        for (const part of item.content) {
          if (part?.type === "output_text" && typeof part.text === "string") {
            text += part.text;
          }
        }
      } else if (item?.type === "function_call") {
        toolCalls.push({
          id: item.call_id || item.id,
          type: "function",
          function: {
            name: item.name,
            arguments: typeof item.arguments === "string" ? item.arguments : JSON.stringify(item.arguments ?? {}),
          },
        });
      }
    }
    return { text, toolCalls };
  }

  /** Convert a Responses API object to a Chat Completions object for clients. */
  _responsesToChatCompletion(response, requestedModel) {
    const { text, toolCalls } = this._extractResponsesContent(response);
    const message = { role: "assistant", content: text };
    if (toolCalls.length > 0) message.tool_calls = toolCalls;
    const usage = response?.usage;
    return {
      id: response?.id ?? `resp-chat-${Date.now()}`,
      object: "chat.completion",
      created: response?.created_at ?? Math.floor(Date.now() / 1000),
      model: requestedModel,
      choices: [
        {
          index: 0,
          message,
          finish_reason: toolCalls.length > 0 ? "tool_calls" : "stop",
        },
      ],
      usage: usage
        ? {
            prompt_tokens: usage.input_tokens ?? 0,
            completion_tokens: usage.output_tokens ?? 0,
            total_tokens: usage.total_tokens ?? (usage.input_tokens ?? 0) + (usage.output_tokens ?? 0),
          }
        : undefined,
    };
  }

  _chatChunk(requestedModel, chunkId, created, delta, finishReason) {
    return (
      `data: ${JSON.stringify({
        id: chunkId,
        object: "chat.completion.chunk",
        created,
        model: requestedModel,
        choices: [{ index: 0, delta, finish_reason: finishReason }],
      })}\n\n`
    );
  }

  /**
   * Consume an upstream Responses SSE byte stream and re-emit Chat
   * Completions SSE chunks, so existing clients (which parse
   * `choices[0].delta.content`) keep working unchanged.
   */
  async _translateResponsesStream(webStream, requestedModel) {
    const reader = webStream.getReader();
    const decoder = new TextDecoder();
    const encoder = new TextEncoder();
    const chunkId = `resp-chat-${Date.now()}`;
    const created = Math.floor(Date.now() / 1000);
    const self = this;

    let buffer = "";
    let sawText = false;

    function emitDelta(text) {
      return self._chatChunk(requestedModel, chunkId, created, { role: "assistant", content: text }, null);
    }

    const out = new ReadableStream({
      async start(controller) {
        const send = (str) => controller.enqueue(encoder.encode(str));
        try {
          for (;;) {
            const { done, value } = await reader.read();
            if (value) buffer += decoder.decode(value, { stream: true });
            if (done) break;
            const events = buffer.split("\n\n");
            buffer = events.pop() ?? "";
            for (const event of events) {
              let dataStr = null;
              for (const line of event.split("\n")) {
                if (line.startsWith("data: ")) dataStr = line.slice(6);
              }
              if (dataStr === null || dataStr === "[DONE]") continue;
              let evt;
              try {
                evt = JSON.parse(dataStr);
              } catch {
                continue;
              }
              if (evt?.type === "response.output_text.delta" && typeof evt.delta === "string") {
                sawText = true;
                send(emitDelta(evt.delta));
              } else if (evt?.type === "response.completed" && evt.response) {
                const { toolCalls } = self._extractResponsesContent(evt.response);
                if (toolCalls.length > 0) {
                  send(
                    self._chatChunk(
                      requestedModel,
                      chunkId,
                      created,
                      { role: "assistant", tool_calls: toolCalls },
                      null
                    )
                  );
                  send(self._chatChunk(requestedModel, chunkId, created, {}, "tool_calls"));
                } else if (!sawText) {
                  // No deltas arrived (some gateways only send the final
                  // object) — emit the full text as one chunk.
                  const { text } = self._extractResponsesContent(evt.response);
                  if (text) send(emitDelta(text));
                  send(self._chatChunk(requestedModel, chunkId, created, {}, "stop"));
                } else {
                  send(self._chatChunk(requestedModel, chunkId, created, {}, "stop"));
                }
              } else if (evt?.type === "error" || evt?.error) {
                send(`data: ${JSON.stringify({ error: evt.error ?? evt })}\n\n`);
              }
            }
          }
        } catch (err) {
          console.error("[responses-stream-translate]", err);
        } finally {
          try {
            controller.enqueue(encoder.encode("data: [DONE]\n\n"));
          } catch {
            // client already gone — nothing to do
          }
          try {
            controller.close();
          } catch {
            // already closed
          }
          try {
            reader.releaseLock();
          } catch {
            // already released
          }
        }
      },
    });
    return Readable.fromWeb(out);
  }

  /**
   * Non-streaming chat completion. Returns the parsed JSON response.
   * @param {object} rawBody - the incoming OpenAI-compatible request body,
   *   with `model` still in `oc/<id>` (passthrough) form.
   */
  async chat(rawBody) {
    const upstreamModelId = this.registry.toUpstreamId(rawBody.model);
    const meta = await this.registry.getModelMeta(rawBody.model).catch(() => null);
    const targetFormat = meta?.targetFormat;
    const isResponses = this._isResponsesTarget(upstreamModelId, targetFormat);
    const payload = this._buildPayload({ ...rawBody, stream: false }, upstreamModelId, targetFormat);

    const res = await this.fetchImpl(this._endpointFor(upstreamModelId, targetFormat), {
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
    const parsed = JSON.parse(text);
    if (isResponses) {
      return this._responsesToChatCompletion(parsed, rawBody.model);
    }
    return parsed;
  }

  /**
   * Streaming chat completion. Returns a Node Readable stream of raw
   * SSE bytes ("data: {...}\n\n" chunks) exactly as upstream sends them —
   * the caller (route handler) is responsible for piping this to the
   * client response untouched. We do NOT buffer the whole response.
   */
  async chatStream(rawBody) {
    const upstreamModelId = this.registry.toUpstreamId(rawBody.model);
    const meta = await this.registry.getModelMeta(rawBody.model).catch(() => null);
    const targetFormat = meta?.targetFormat;
    const isResponses = this._isResponsesTarget(upstreamModelId, targetFormat);
    const payload = this._buildPayload({ ...rawBody, stream: true }, upstreamModelId, targetFormat);

    const res = await this.fetchImpl(this._endpointFor(upstreamModelId, targetFormat), {
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
    if (isResponses) {
      // Translate Responses SSE events to Chat Completions chunks so
      // existing clients keep parsing `choices[0].delta.content`.
      return this._translateResponsesStream(res.body, rawBody.model);
    }
    return Readable.fromWeb(res.body);
  }
}

export default OpenCodeConnector;
