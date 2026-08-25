// routes/chat.js
import { Router } from "express";

/**
 * @param {import("../lib/modelRegistry.js").ModelRegistry} registry
 * @param {import("../lib/opencodeConnector.js").OpenCodeConnector} connector
 */
export function buildChatRouter(registry, connector) {
  const router = Router();

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

    try {
      if (body.stream) {
        const upstreamStream = await connector.chatStream(body);

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

      const completion = await connector.chat(body);
      res.json(completion);
    } catch (err) {
      console.error("[POST /v1/chat/completions]", err);
      const status = err.status && err.status >= 400 && err.status < 600 ? err.status : 502;
      res.status(status).json({
        error: { message: err.message, type: "upstream_error" },
      });
    }
  });

  return router;
}

export default buildChatRouter;
