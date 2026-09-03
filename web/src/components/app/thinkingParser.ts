/**
 * Split a model reply into an optional thinking section and the final answer.
 * Pure function (no JSX) so it can be unit-tested with plain node.
 *
 * Detected shapes (checked in order):
 *  1. `<think>...</think>` tags (common reasoning format).
 *  2. A leading "Here's a thinking process" style preamble closed by a `✅`
 *     marker — the convention this deployment's models use (thinking steps
 *     followed by `✅` + the finalized answer).
 *  3. A `Thinking:` / `**Thinking:**` header block ending at the first
 *     blank line followed by non-list content... (conservative: only when
 *     the header is at the very start).
 *
 * Anything else returns `{ thinking: null, answer: text }` untouched, so
 * normal answers never get mangled.
 */
export interface SplitResult {
  thinking: string | null;
  answer: string;
}

export function splitThinking(text: string): SplitResult {
  if (!text) return { thinking: null, answer: text };

  // 1. <think>...</think>
  const thinkTag = text.match(/<think>([\s\S]*?)<\/think>/i);
  if (thinkTag) {
    const answer = (text.slice(0, thinkTag.index ?? 0) + text.slice((thinkTag.index ?? 0) + thinkTag[0].length)).trim();
    return { thinking: thinkTag[1].trim() || null, answer: answer || text };
  }

  // 2. "Here's a thinking process ..." ... ✅ ... <final answer>
  if (/^\s*(here'?s? a thinking process|thinking process|my thinking|reasoning)\b/im.test(text)) {
    const marker = text.lastIndexOf("✅");
    if (marker !== -1) {
      const thinking = text.slice(0, marker).trim();
      const answer = text.slice(marker + "✅".length).trim();
      if (thinking && answer) return { thinking, answer };
    }
  }

  // 3. Leading "Thinking:" header block (up to first blank line).
  const headerBlock = text.match(/^\s*(\*\*)?thinking:(\*\*)?\s*\n([\s\S]*?)\n\s*\n([\s\S]+)$/i);
  if (headerBlock) {
    const thinking = headerBlock[3].trim();
    const answer = headerBlock[4].trim();
    if (thinking && answer) return { thinking, answer };
  }

  return { thinking: null, answer: text };
}
