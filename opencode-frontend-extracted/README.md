# opencode-bridge

OpenAI-compatible HTTP bridge to OpenCode Zen, built exactly around the
provider shape you gave:

```js
models: [],
modelsFetcher: { url: "https://opencode.ai/zen/v1/models", type: "opencode-free" },
passthroughModels: true,
```

No `opencode` CLI, no subprocess spawning — just HTTP.

## Files

| File | Purpose |
|---|---|
| `providers/opencode.js` | The provider config — your pasted object, unchanged. Single source of truth for base URL, headers, alias. |
| `lib/modelRegistry.js` | Fetches `/zen/v1/models`, caches it (10 min default), prefixes ids as `oc/<id>`, background auto-refresh, `oc/` <-> raw id translation. |
| `lib/opencodeConnector.js` | HTTP client for `/zen/v1/chat/completions` — both buffered and SSE-streaming, with a field allowlist so unsupported params get dropped instead of forced. |
| `routes/models.js` | `GET /v1/models` — serves the cached, prefixed list in OpenAI format. |
| `routes/chat.js` | `POST /v1/chat/completions` — validates, strips `oc/`, forwards, streams the SSE response straight through without buffering. |
| `server.js` | Wires it all into Express, starts the background refresh loop, listens on `PORT`. |
| `scripts/test-*.js` | Runnable versions of the curl checks (models, chat, streaming). |

## Run it

```bash
npm install
cp .env.example .env      # optional — provider is no-auth by default
npm start
```

Then in another terminal:

```bash
npm run test:models
npm run test:chat
npm run test:stream
```

## Wire it into your frontend

Point your model dropdown at `GET http://localhost:8787/v1/models` — it
returns ids already in `oc/<model>` form, e.g. `oc/big-pickle`,
`oc/claude-sonnet-5`, `oc/nemotron-3.5-lightning-free`. Send chat
requests to `POST /v1/chat/completions` with that same `oc/`-prefixed id
in the `model` field — the bridge strips the prefix before it reaches
OpenCode Zen.

## Design notes / gotchas already handled

- **No hardcoded model list.** `providers/opencode.js` keeps `models: []`
  on purpose — `modelRegistry.js` is the only place a model list is
  materialized, and it's always live.
- **`big-pickle` has no `-free` suffix.** `isFreeModelId()` special-cases
  it rather than relying purely on `.endsWith("-free")`.
- **No-auth providers don't get filtered out.** `noAuth: true` is
  respected — the connector only attaches `Authorization` if you
  actually set `OPENCODE_API_KEY`.
- **Streaming isn't buffered.** `chatStream()` returns a raw Node
  `Readable` piped directly into the Express response — token-by-token
  delivery, not "wait for the whole thing then dump it."
- **Cache doesn't stampede.** Concurrent requests during a cold cache
  are deduped into one upstream fetch; on a refresh failure it falls
  back to serving the last good cache instead of 500ing.
- **Not every model is guaranteed `/chat/completions`-shaped.** If you
  later add Responses-API models (the `gpt-5.6-*` family upstream), add
  a capability map and branch in `_endpointFor()` — don't assume by
  name pattern.

## Extending

- To require auth for your own frontend → clients, add your own
  middleware in `server.js` before the routers; the bridge's *own* call
  to OpenCode Zen stays no-auth regardless.
- To add a second provider (e.g. a paid tier), copy the
  `providers/opencode.js` shape, give it its own `ModelRegistry` +
  `OpenCodeConnector` instance, and merge both model lists in
  `routes/models.js`.
