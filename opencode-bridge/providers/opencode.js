// providers/opencode.js
//
// This is the provider definition — the "contract" the rest of the bridge
// reads from. Nothing else in the codebase should hardcode a model list,
// a base URL, or auth behavior. If OpenCode Zen changes its upstream URL
// or headers, this is the only file that should need to change.

export const openCodeProvider = {
  id: "opencode",
  priority: 40,
  hasFree: true,

  alias: "oc",
  uiAlias: "oc",

  display: {
    name: "OpenCode Free",
    icon: "terminal",
    color: "#E87040",
    textIcon: "OC",
  },

  category: "free",
  noAuth: true,

  transport: {
    baseUrl: "https://opencode.ai",
    headers: {
      "x-opencode-client": "desktop",
    },
    noAuth: true,
  },

  // Muse Spark models are served by /zen/v1/responses; the rest stay on
  // /chat/completions, so the format is declared per-model, not per-provider.
  models: [
    { id: "muse-spark-1.2-contributor-free", name: "Muse Spark 1.2 Contributor Free", targetFormat: "openai-responses" },
    { id: "muse-spark-1.3-contributor-free", name: "Muse Spark 1.3 Contributor Free", targetFormat: "openai-responses" },
  ],

  modelsFetcher: {
    url: "https://opencode.ai/zen/v1/models",
    type: "opencode-free",
  },

  // oc/<whatever-upstream-model-id-is> — we never invent our own IDs,
  // we just prefix whatever upstream returns.
  passthroughModels: true,
};

export default openCodeProvider;

