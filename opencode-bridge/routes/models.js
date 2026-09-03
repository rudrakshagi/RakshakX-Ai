// routes/models.js
import { Router } from "express";

/**
 * @param {import("../lib/modelRegistry.js").ModelRegistry} registry
 */
export function buildModelsRouter(registry) {
  const router = Router();

  // GET /v1/models -> OpenAI-format list, ids already prefixed oc/<id>
  router.get("/v1/models", async (req, res) => {
    try {
      const forceRefresh = req.query.refresh === "1";
      const models = await registry.getModels({ forceRefresh });

      res.json({
        object: "list",
        data: models.map((m) => ({
          id: m.id,
          name: m.name ?? m.id,
          object: "model",
          created: m.created ?? Math.floor(Date.now() / 1000),
          owned_by: m.owned_by ?? "opencode",
          ...(m.targetFormat ? { targetFormat: m.targetFormat } : {}),
        })),
      });
    } catch (err) {
      console.error("[GET /v1/models]", err);
      res.status(502).json({
        error: { message: `Failed to fetch model list: ${err.message}`, type: "upstream_error" },
      });
    }
  });

  return router;
}

export default buildModelsRouter;
