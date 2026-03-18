import { ContentBlock } from "@langchain/core/messages";

/**
 * Converts a File object to a LangChain ContentBlock suitable for
 * multimodal messages. Supports images (JPEG, PNG, GIF, WEBP) and PDFs.
 */
export async function fileToContentBlock(
  file: File,
): Promise<ContentBlock.Multimodal.Data> {
  const buffer = await file.arrayBuffer();
  const base64 = btoa(
    new Uint8Array(buffer).reduce(
      (data, byte) => data + String.fromCharCode(byte),
      "",
    ),
  );

  if (file.type === "application/pdf") {
    return {
      type: "file",
      mimeType: "application/pdf",
      data: base64,
      metadata: {
        filename: file.name,
        name: file.name,
      },
    } as ContentBlock.Multimodal.Data;
  }

  // Image types
  return {
    type: "image",
    mimeType: file.type,
    data: base64,
    metadata: {
      name: file.name,
    },
  } as ContentBlock.Multimodal.Data;
}

/**
 * Checks whether a content block is a base64-encoded multimodal block
 * (image or file with data).
 */
export function isBase64ContentBlock(
  block: unknown,
): block is ContentBlock.Multimodal.Data {
  if (!block || typeof block !== "object") return false;
  const b = block as Record<string, unknown>;

  if (b.type === "image" && typeof b.data === "string" && b.mimeType) {
    return true;
  }

  if (b.type === "file" && typeof b.data === "string" && b.mimeType) {
    return true;
  }

  return false;
}
