// routes/chat.js
import { Router } from "express";
import { agentManager } from "./agents.js";
import { RAKSHAK_TOOLS } from "../lib/rakshakTools.js";
import { ToolExecutor } from "../lib/toolExecutor.js";
import { resolveApproval, APPROVAL_MANUAL } from "../lib/approval.js";

const MAX_TURNS = 6;

function parseArgs(raw) {
  if (!raw) return {};
  if (typeof raw === "object") return raw;
  try {
    return JSON.parse(raw);
  } catch {
    return { _raw: String(raw) };
  }
}

/** Emit a completed Chat Completion as SSE chunks (content deltas + [DONE]). */
async function emitAsSSE(res, completion) {
  const choice = completion?.choices?.[0];
  const msg = choice?.message ?? {};
  const content = msg.content ?? "";
  const id = completion?.id ?? `chatcmpl-${Date.now()}`;
  const model = completion?.model ?? "unknown";
  const created = Math.floor(Date.now() / 1000);
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  const send = (obj) => res.write(`data: ${JSON.stringify(obj)}\n\n`);
  const chunk = (delta, finish) => send({ id, object: "chat.completion.chunk", created, model, choices: [{ index: 0, delta, finish_reason: finish ?? null }] });
  chunk({ role: "assistant" }, null);
  if (typeof content === "string" && content.length > 0) {
    // Stream in small token-like slices with micro-delays for smooth live streaming feel
    const SLICE = 12;
    for (let i = 0; i < content.length; i += SLICE) {
      chunk({ content: content.slice(i, i + SLICE) }, null);
      await new Promise((r) => setTimeout(r, 16));
    }
  }
  if (msg.tool_calls) chunk({ tool_calls: msg.tool_calls }, null);
  chunk({}, choice?.finish_reason ?? "stop");
  res.write("data: [DONE]\n\n");
  res.end();
}

/**
 * @param {import("../lib/modelRegistry.js").ModelRegistry} registry
 * @param {import("../lib/opencodeConnector.js").OpenCodeConnector} connector
 */
export function buildChatRouter(registry, connector) {
  const router = Router();
  const executor = new ToolExecutor({
    backendBase: process.env.RAKSHAK_BACKEND ?? "http://127.0.0.1:8080",
  });

  router.post("/v1/chat/completions", async (req, res) => {
    const body = req.body ?? {};

    if (!body.model) {
      return res.status(400).json({ error: { message: "`model` is required", type: "invalid_request" } });
    }
    if (!Array.isArray(body.messages) || body.messages.length === 0) {
      return res
        .status(400)
        .json({ error: { message: "`messages` must be a non-empty array", type: "invalid_request" } });
    }

    // Optional: reject unknown models early with a clean 404 instead of
    // letting upstream error out. Comment this out if you'd rather let
    // OpenCode Zen be the source of truth for validity.
    const known = await registry.isKnownModel(body.model).catch(() => true); // fail open if registry is down
    if (!known) {
      return res.status(404).json({
        error: { message: `Unknown model "${body.model}". Call GET /v1/models for the current list.`, type: "invalid_request" },
      });
    }

    // --- agentic tool setup -------------------------------------------------
    // If the client sent explicit tools or set use_rakshak_tools === true, activate tools.
    // Default to false for standard chat to prevent small models from hallucinating on 23 complex tool schemas.
    const clientTools = Array.isArray(body.tools) ? body.tools : null;
    const useRakshakTools = body.use_rakshak_tools === true;
    const effectiveTools = clientTools ?? (useRakshakTools ? RAKSHAK_TOOLS : undefined);
    const toolsActive = Array.isArray(effectiveTools) && effectiveTools.length > 0;
    const approval = body.approval ?? { mode: "auto" };
    const decisions = approval.decisions ?? {};
    // Normalize once (resolveApproval would warn per tool-call otherwise).
    const approvalMode = approval.mode ?? "auto";
    if (approvalMode !== "auto" && approvalMode !== APPROVAL_MANUAL) {
      console.warn(`[chat.js] unknown approval.mode "${approvalMode}"; treating as "auto".`);
    }
    const effectiveApprovalMode = approvalMode === APPROVAL_MANUAL ? APPROVAL_MANUAL : "auto";
    const wantStream = Boolean(body.stream);

    // Strip bridge-only fields before forwarding upstream.
    const { approval: _dropApproval, use_rakshak_tools: _dropTools, ...clientBody } = body;

    async function runAgenticLoop() {
      const messages = [...clientBody.messages];
      let lastCompletion = null;
      const executedResults = [];
      // Sticky denies: a DENIED destructive call re-issued with a fresh
      // call_id but identical name+args stays denied without re-prompting.
      const deniedKeys = new Set();
      // Fallback model is shared across turns: once we fall back, stay on
      // the working model for the rest of the loop (don't flap per turn).
      let loopModel = clientBody.model;

      for (let turn = 0; turn < MAX_TURNS; turn++) {
        const sanitizedMessages = messages.map((m) => {
          const c = { ...m };
          if (!c.content && (!c.tool_calls || c.tool_calls.length === 0)) {
            c.content = "Executing requested tool...";
          }
          return c;
        });

        const upstreamBody = {
          ...clientBody,
          model: loopModel,
          messages: sanitizedMessages,
          stream: false,
          ...(toolsActive ? { tools: effectiveTools, tool_choice: clientBody.tool_choice ?? "auto" } : {}),
        };

        let completion;
        try {
          const res = await connector.chatWithFallback(upstreamBody);
          completion = res.completion;
          if (res.fallbackUsed) loopModel = res.fallbackModel;
        } catch (err) {
          if (turn > 0 && executedResults.length > 0) {
            console.warn("[chat.js] Upstream error after tool execution; synthesizing tool response:", err.message);
            const summary = executedResults.map((r) => `### Tool Execution: ${r.name}\n\`\`\`\n${r.output}\n\`\`\``).join("\n\n");
            return {
              completion: {
                id: `chatcmpl-${Date.now()}`,
                object: "chat.completion",
                created: Math.floor(Date.now() / 1000),
                model: body.model,
                choices: [
                  {
                    index: 0,
                    message: { role: "assistant", content: `Here are the tool execution results:\n\n${summary}` },
                    finish_reason: "stop",
                  },
                ],
              },
              approvalRequired: false,
            };
          }
          throw err;
        }

        lastCompletion = completion;
        const choice = completion?.choices?.[0];
        const msg = choice?.message;
        if (choice?.finish_reason !== "tool_calls" || !Array.isArray(msg?.tool_calls) || msg.tool_calls.length === 0) {
          // If model finished after tools but left content empty, synthesize from executed results
          if ((!msg?.content || msg.content.trim() === "") && executedResults.length > 0) {
            const summary = executedResults.map((r) => `### Tool Result: ${r.name}\n\`\`\`\n${r.output}\n\`\`\``).join("\n\n");
            choice.message.content = `Completed tool execution:\n\n${summary}`;
          }
          return { completion, approvalRequired: false };
        }

        // Append assistant tool-call message to history.
        messages.push({ role: "assistant", content: msg.content || "Executing tools...", tool_calls: msg.tool_calls });

        const pendingApprovals = [];
        let stoppedForApproval = false;

        for (const tc of msg.tool_calls) {
          const callId = tc.id;
          const name = tc.function?.name;
          const args = parseArgs(tc.function?.arguments);

          const gate = resolveApproval({
            mode: effectiveApprovalMode,
            decisions,
            deniedKeys,
            callId,
            name,
            args,
          });
          if (gate.action === "deny") {
            messages.push({ role: "tool", tool_call_id: callId, content: "DENIED_BY_USER" });
            continue;
          }
          if (gate.action === "pend") {
            pendingApprovals.push({ call_id: callId, name, arguments: tc.function?.arguments });
            stoppedForApproval = true;
            continue;
          }

          const out = await executor.executeOne({ name, args });
          executedResults.push({ name, args, output: out.resultText });
          messages.push({ role: "tool", tool_call_id: callId, content: out.resultText });
        }

        if (stoppedForApproval) {
          return {
            completion: {
              id: lastCompletion?.id ?? `chatcmpl-${Date.now()}`,
              object: "chat.completion",
              created: Math.floor(Date.now() / 1000),
              model: body.model,
              choices: [
                {
                  index: 0,
                  message: { role: "assistant", content: msg.content ?? "", tool_calls: msg.tool_calls },
                  finish_reason: "approval_required",
                  pending_approvals: pendingApprovals,
                },
              ],
            },
            approvalRequired: true,
          };
        }
      }

      if (lastCompletion?.choices?.[0]?.message && (!lastCompletion.choices[0].message.content || lastCompletion.choices[0].message.content.trim() === "") && executedResults.length > 0) {
        const summary = executedResults.map((r) => `### Tool Result: ${r.name}\n\`\`\`\n${r.output}\n\`\`\``).join("\n\n");
        lastCompletion.choices[0].message.content = `Completed tool execution:\n\n${summary}`;
      }

      return { completion: lastCompletion, approvalRequired: false };
    }

    try {
      if (wantStream && !toolsActive) {
        // No tools: preserve original token-by-token passthrough.
        const upstreamStream = await connector.chatStream(clientBody);

        res.setHeader("Content-Type", "text/event-stream");
        res.setHeader("Cache-Control", "no-cache");
        res.setHeader("Connection", "keep-alive");
        res.flushHeaders?.();

        upstreamStream.on("error", (err) => {
          console.error("[POST /v1/chat/completions] stream error", err);
          if (!res.writableEnded) res.end();
        });
        req.on("close", () => upstreamStream.destroy());

        // Passthrough — do not buffer, do not re-parse. This preserves
        // token-by-token delivery to the client.
        upstreamStream.pipe(res);
        return;
      }

      if (toolsActive) {
        const { completion } = await runAgenticLoop();
        if (wantStream) {
          emitAsSSE(res, completion);
          return;
        }
        res.json(completion);
        return;
      }

      const completion = (await connector.chatWithFallback(clientBody)).completion;
      res.json(completion);
    } catch (err) {
      console.error("[POST /v1/chat/completions]", err);
      const status = err.status && err.status >= 400 && err.status < 600 ? err.status : 502;
      if (!res.headersSent) {
        res.status(status).json({
          error: { message: err.message, type: "upstream_error" },
        });
      } else {
        res.end();
      }
    }
  });

  return router;
}

export default buildChatRouter;
