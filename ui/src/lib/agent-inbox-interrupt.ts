import { Interrupt } from "@langchain/langgraph-sdk";
import { HITLRequest } from "@/components/thread/agent-inbox/types";

/**
 * Type guard that checks whether an unknown interrupt value conforms to
 * the Agent Inbox HITL interrupt schema (single or array).
 */
export function isAgentInboxInterruptSchema(
  interrupt: unknown,
): interrupt is Interrupt<HITLRequest> | Interrupt<HITLRequest>[] {
  if (!interrupt) return false;

  const items = Array.isArray(interrupt) ? interrupt : [interrupt];

  return items.every((item) => {
    if (!item || typeof item !== "object") return false;

    const value = (item as Record<string, unknown>).value;
    if (!value || typeof value !== "object") return false;

    const v = value as Record<string, unknown>;

    return (
      Array.isArray(v.action_requests) &&
      v.action_requests.length > 0 &&
      Array.isArray(v.review_configs)
    );
  });
}
