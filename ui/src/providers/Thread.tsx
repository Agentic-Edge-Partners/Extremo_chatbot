import { validate } from "uuid";
import { getApiKey } from "@/lib/api-key";
import { Thread } from "@langchain/langgraph-sdk";
import {
  createContext,
  useContext,
  ReactNode,
  useCallback,
  useState,
  Dispatch,
  SetStateAction,
} from "react";
import { createClient } from "./client";
import { useAuth } from "./Auth";

const DEFAULT_API_URL = "http://localhost:2024";
const DEFAULT_ASSISTANT_ID = "agent";

interface ThreadContextType {
  getThreads: () => Promise<Thread[]>;
  threads: Thread[];
  setThreads: Dispatch<SetStateAction<Thread[]>>;
  threadsLoading: boolean;
  setThreadsLoading: Dispatch<SetStateAction<boolean>>;
  updateThreadEventName: (threadId: string, eventName: string) => Promise<void>;
}

const ThreadContext = createContext<ThreadContextType | undefined>(undefined);

function getThreadSearchMetadata(
  assistantId: string,
  username: string | null,
): Record<string, string> {
  const metadata: Record<string, string> = {};

  if (validate(assistantId)) {
    metadata.assistant_id = assistantId;
  } else {
    metadata.graph_id = assistantId;
  }

  // Filter by username if authenticated
  if (username) {
    metadata.username = username;
  }

  return metadata;
}

export function ThreadProvider({ children }: { children: ReactNode }) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;
  const assistantId = process.env.NEXT_PUBLIC_ASSISTANT_ID || DEFAULT_ASSISTANT_ID;
  const [threads, setThreads] = useState<Thread[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(false);
  const { username } = useAuth();

  const getThreads = useCallback(async (): Promise<Thread[]> => {
    if (!apiUrl || !assistantId) return [];
    const client = createClient(apiUrl, getApiKey() ?? undefined);

    const threads = await client.threads.search({
      metadata: getThreadSearchMetadata(assistantId, username),
      limit: 100,
    });

    return threads;
  }, [apiUrl, assistantId, username]);

  const updateThreadEventName = useCallback(
    async (threadId: string, eventName: string) => {
      if (!apiUrl) return;
      const client = createClient(apiUrl, getApiKey() ?? undefined);
      await client.threads.update(threadId, {
        metadata: { event_name: eventName },
      });
      // Refresh threads list
      const updated = await getThreads();
      setThreads(updated);
    },
    [apiUrl, getThreads],
  );

  const value = {
    getThreads,
    threads,
    setThreads,
    threadsLoading,
    setThreadsLoading,
    updateThreadEventName,
  };

  return (
    <ThreadContext.Provider value={value}>{children}</ThreadContext.Provider>
  );
}

export function useThreads() {
  const context = useContext(ThreadContext);
  if (context === undefined) {
    throw new Error("useThreads must be used within a ThreadProvider");
  }
  return context;
}
