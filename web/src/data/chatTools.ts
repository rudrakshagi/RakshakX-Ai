/** Shared helpers for agentic chat tool calls + approval flow. */

export interface ChatToolCall {
  call_id: string;
  name: string;
  arguments: string;
}

/** Tools that always require explicit confirmation unless chat-level auto-approve is on. */
export const DESTRUCTIVE_TOOLS: string[] = [
  'start_scan',
  'agent_spawn',
  'agent_stop',
  'exec_command',
  'finish_scan',
];

export const CHAT_APPROVAL_STORAGE_KEY = 'rakshakx_chat_approval_v1';

interface RawToolCall {
  id?: string;
  call_id?: string;
  type?: string;
  function?: { name?: string; arguments?: string };
  name?: string;
  arguments?: string;
  argsText?: string;
}

/**
 * Extract OpenAI-style `tool_calls` from a chat message into the
 * flat `{call_id, name, arguments}` shape used by the approval card.
 * Accepts both `tool_calls` (new) and legacy `toolCalls` fields.
 */
export function parseToolCallsFromMessage(msg: {
  tool_calls?: RawToolCall[];
  toolCalls?: { id: string; name: string; args: string }[];
}): ChatToolCall[] {
  if (Array.isArray(msg.tool_calls)) {
    return msg.tool_calls.map((tc) => ({
      call_id: String(tc?.id ?? tc?.call_id ?? ''),
      name: String(tc?.function?.name ?? tc?.name ?? 'unknown_tool'),
      arguments: String(tc?.function?.arguments ?? tc?.arguments ?? tc?.argsText ?? ''),
    }));
  }
  if (Array.isArray(msg.toolCalls)) {
    return msg.toolCalls.map((tc) => ({
      call_id: String(tc.id),
      name: String(tc.name),
      arguments: String(tc.args),
    }));
  }
  return [];
}

/** Build the `approval` payload sent alongside `/v1/chat/completions`. */
export function buildApprovalBody(
  autoApprove: boolean,
  decisions: Record<string, 'approve' | 'deny'>,
): { mode: 'auto' | 'manual'; decisions: Record<string, 'approve' | 'deny'> } {
  return {
    mode: autoApprove ? 'auto' : 'manual',
    decisions,
  };
}
