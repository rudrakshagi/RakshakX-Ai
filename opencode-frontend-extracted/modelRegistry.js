// lib/modelRegistry.js
//
// Handles model discovery for a provider that uses the
// `models: [] + modelsFetcher + passthroughModels: true` pattern.
//
// Responsibilities:
//  - fetch the upstream model list (GET modelsFetcher.url)
//  - cache it (default 10 min TTL) so we don't hit /zen/v1/models on
//    every single chat request
//  - prefix every upstream id with `${alias}/` (oc/<id>) before it's
//    ever shown to the frontend
//  - background auto-refresh so newly released free models show up
//    without a restart
//  - NEVER filter models based on auth requirements — a no-auth
//    provider's models must not get silently dropped (this bit 9Router
//    in the past, see the "big-pickle has no -free suffix" trap below)

const DEFAULT_TTL_MS = 10 * 60 * 1000; // 10 minutes

export class ModelRegistry {
  /**
   * @param {object} provider - a provider object shaped like providers/opencode.js
   * @param {object} [opts]
   * @param {number} [opts.ttlMs] - cache TTL in ms
   * @param {typeof fetch} [opts.fetchImpl] - injectable fetch for testing
   */
  constructor(provider, opts = {}) {
    this.provider = provider;
    this.ttlMs = opts.ttlMs ?? DEFAULT_TTL_MS;
    this.fetchImpl = opts.fetchImpl ?? fetch;

    this._cache = null; // { fetchedAt, upstreamModels, passthroughModels }
    this._refreshTimer = null;
    this._inFlight = null; // dedupe concurrent fetches
  }

  /**
   * Returns the passthrough-prefixed model list, using cache when fresh.
   * Always resolves — falls back to stale cache on fetch failure rather
   * than throwing, so a transient upstream blip doesn't 500 the whole
   * /v1/models endpoint.
   */
  async getModels({ forceRefresh = false } = {}) {
    const isFresh = this._cache && Date.now() - this._cache.fetchedAt < this.ttlMs;

    if (!forceRefresh && isFresh) {
      return this._cache.passthroughModels;
    }

    try {
      return await this._fetchAndCache();
    } catch (err) {
      if (this._cache) {
        console.warn(
          `[modelRegistry] refresh failed (${err.message}), serving stale cache from ${new Date(
            this._cache.fetchedAt
          ).toISOString()}`
        );
        return this._cache.passthroughModels;
      }
      throw err; // no cache at all yet — nothing to fall back to
    }
  }

  /** Raw upstream model objects, unprefixed (rarely needed directly). */
  async getUpstreamModels(opts) {
    await this.getModels(opts);
    return this._cache.upstreamModels;
  }

  /** True if `passthroughId` (e.g. "oc/big-pickle") exists in the current model list. */
  async isKnownModel(passthroughId, opts) {
    const models = await this.getModels(opts);
    return models.some((m) => m.id === passthroughId);
  }

  /**
   * Heuristic free-tier check. Prefer trusting whatever upstream marks
   * as free (if it ever adds that metadata) over name-sniffing — but
   * since /zen/v1/models today doesn't expose a `free` flag, we sniff
   * the id with a known exceptions list.
   *
   * Trap to avoid: don't just check `.endsWith("-free")`. "big-pickle"
   * is a free model with no -free suffix. Keep this list updated, or
   * better, replace it once upstream exposes real pricing metadata.
   */
  isFreeModelId(upstreamId) {
    const KNOWN_FREE_WITHOUT_SUFFIX = new Set(["big-pickle"]);
    return upstreamId.endsWith("-free") || KNOWN_FREE_WITHOUT_SUFFIX.has(upstreamId);
  }

  /** Strips the `oc/` alias prefix. "oc/big-pickle" -> "big-pickle". Passes through unprefixed ids untouched. */
  toUpstreamId(passthroughId) {
    const prefix = `${this.provider.alias}/`;
    return passthroughId.startsWith(prefix) ? passthroughId.slice(prefix.length) : passthroughId;
  }

  /** Adds the `oc/` alias prefix. "big-pickle" -> "oc/big-pickle". */
  toPassthroughId(upstreamId) {
    return `${this.provider.alias}/${upstreamId}`;
  }

  /** Starts a background timer that refreshes the cache every `intervalMs`. */
  startAutoRefresh(intervalMs = this.ttlMs) {
    this.stopAutoRefresh();
    this._refreshTimer = setInterval(() => {
      this._fetchAndCache().catch((err) =>
        console.warn(`[modelRegistry] background refresh failed: ${err.message}`)
      );
    }, intervalMs);
    // Don't let this timer keep the process alive on its own.
    this._refreshTimer.unref?.();
  }

  stopAutoRefresh() {
    if (this._refreshTimer) {
      clearInterval(this._refreshTimer);
      this._refreshTimer = null;
    }
  }

  async _fetchAndCache() {
    // Dedupe concurrent callers (e.g. several requests arriving while
    // the cache is cold) into a single upstream request.
    if (this._inFlight) return this._inFlight.then(() => this._cache.passthroughModels);

    this._inFlight = (async () => {
      const { url } = this.provider.modelsFetcher;
      const headers = { ...this.provider.transport.headers };

      const res = await this.fetchImpl(url, { headers });
      if (!res.ok) {
        throw new Error(`modelsFetcher GET ${url} -> ${res.status} ${res.statusText}`);
      }

      const body = await res.json();
      const upstreamModels = Array.isArray(body?.data) ? body.data : [];

      const passthroughModels = this.provider.passthroughModels
        ? upstreamModels.map((m) => ({
            ...m,
            id: this.toPassthroughId(m.id),
            _upstreamId: m.id,
            _free: this.isFreeModelId(m.id),
          }))
        : upstreamModels;

      this._cache = { fetchedAt: Date.now(), upstreamModels, passthroughModels };
    })();

    try {
      await this._inFlight;
    } finally {
      this._inFlight = null;
    }

    return this._cache.passthroughModels;
  }
}

export default ModelRegistry;
