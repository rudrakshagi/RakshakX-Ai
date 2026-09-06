# Future Work

## 9Router as fallback LLM provider (NOT implemented yet)

**Status:** parked — implement later on demand.

**Context:** 9Router has zero live usage in the codebase today. The only mention is a
historical comment in `opencode-bridge/lib/modelRegistry.js:15` ("this bit 9Router in the
past" — auth-based filtering once silently dropped its models). The bridge currently runs
100% on OpenCode Zen (`opencode-bridge/providers/opencode.js` → `https://opencode.ai`).

**When we pick this up, do:**
1. Add `opencode-bridge/providers/ninerouter.js` shaped like `providers/opencode.js`
   (id, alias e.g. `nr`, transport baseUrl + headers/auth, `modelsFetcher`, `passthroughModels`).
2. Extend `lib/modelRegistry.js` to merge multiple providers (prefix `nr/<id>`,
   keep the no-auth-drop lesson: never silently drop models on auth).
3. Extend `lib/opencodeConnector.js` with per-provider endpoint routing + failover
   (try Zen, fall back to 9Router on 429/5xx).
4. Add `NINEROUTER_API_KEY` to `opencode-bridge/.env.example` + `.env`.
5. Add scripts `test-fallback.js` (kill primary, assert fallback serves chat).
6. Update `web/src/data/chatTools.ts` / model picker if provider-prefixed ids need UI grouping.

**Do NOT touch until requested:** `routes/chat.js` approval loop, `lib/toolExecutor.js`,
`routes/agents.js` live proxy — those are provider-agnostic already.
