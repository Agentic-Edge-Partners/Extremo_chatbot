import { v4 as uuidv4 } from "uuid";
import { Message } from "@langchain/langgraph-sdk";

export const DO_NOT_RENDER_ID_PREFIX = "__do_not_render__";

/**
 * Ensures that every AI message with tool_calls has a corresponding
 * tool response message. If a tool call is missing a response, a
 * synthetic tool message is inserted so the conversation remains valid.
 */
export function ensureToolCallsHaveResponses(
  messages: Message[],
): Message[] {
  const result: Message[] = [];

  for (const message of messages) {
    result.push(message);

    if (
      message.type === "ai" &&
      "tool_calls" in message &&
      Array.isArray(message.tool_calls) &&
      message.tool_calls.length > 0
    ) {
      for (const toolCall of message.tool_calls) {
        const hasResponse = messages.some(
          (m) =>
            m.type === "tool" &&
            "tool_call_id" in m &&
            m.tool_call_id === toolCall.id,
        );

        if (!hasResponse) {
          result.push({
            id: `${DO_NOT_RENDER_ID_PREFIX}${uuidv4()}`,
            type: "tool",
            content:
              "This tool call was interrupted and did not receive a response.",
            tool_call_id: toolCall.id,
            name: toolCall.name,
          } as Message);
        }
      }
    }
  }

  return result;
}
