import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useThreads } from "@/providers/Thread";
import { useAuth } from "@/providers/Auth";
import { Thread } from "@langchain/langgraph-sdk";
import { useEffect, useState } from "react";

import { getContentString } from "../utils";
import { useQueryState, parseAsBoolean } from "nuqs";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import {
  PanelRightOpen,
  PanelRightClose,
  LogOut,
  Tag,
  Check,
  X,
} from "lucide-react";
import { useMediaQuery } from "@/hooks/useMediaQuery";

function EventNameEditor({
  threadId,
  currentName,
}: {
  threadId: string;
  currentName: string;
}) {
  const { updateThreadEventName } = useThreads();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(currentName);

  if (!editing) {
    return (
      <button
        onClick={(e) => {
          e.stopPropagation();
          setEditing(true);
        }}
        className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600"
        title="Tag with event name"
      >
        <Tag className="size-3" />
        {currentName || "Add event tag"}
      </button>
    );
  }

  return (
    <div
      className="flex items-center gap-1"
      onClick={(e) => e.stopPropagation()}
    >
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            updateThreadEventName(threadId, value);
            setEditing(false);
          }
          if (e.key === "Escape") {
            setValue(currentName);
            setEditing(false);
          }
        }}
        className="h-6 text-xs"
        placeholder="e.g. Vodafone March 2025"
        autoFocus
      />
      <button
        onClick={() => {
          updateThreadEventName(threadId, value);
          setEditing(false);
        }}
        className="text-green-600 hover:text-green-800"
      >
        <Check className="size-3" />
      </button>
      <button
        onClick={() => {
          setValue(currentName);
          setEditing(false);
        }}
        className="text-gray-400 hover:text-gray-600"
      >
        <X className="size-3" />
      </button>
    </div>
  );
}

function ThreadList({
  threads,
  onThreadClick,
}: {
  threads: Thread[];
  onThreadClick?: (threadId: string) => void;
}) {
  const [threadId, setThreadId] = useQueryState("threadId");

  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-1 overflow-y-scroll px-1 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-track]:bg-transparent">
      {threads.map((t) => {
        let itemText = t.thread_id;
        if (
          typeof t.values === "object" &&
          t.values &&
          "messages" in t.values &&
          Array.isArray(t.values.messages) &&
          t.values.messages?.length > 0
        ) {
          const firstMessage = t.values.messages[0];
          itemText = getContentString(firstMessage.content);
        }

        const eventName =
          (t.metadata as Record<string, string> | undefined)?.event_name || "";

        return (
          <div key={t.thread_id} className="w-full">
            <Button
              variant="ghost"
              className={`w-[280px] flex-col items-start justify-start gap-0.5 py-2 text-left font-normal ${
                t.thread_id === threadId ? "bg-gray-100" : ""
              }`}
              onClick={(e) => {
                e.preventDefault();
                onThreadClick?.(t.thread_id);
                if (t.thread_id === threadId) return;
                setThreadId(t.thread_id);
              }}
            >
              <p className="w-full truncate text-ellipsis text-sm">
                {itemText}
              </p>
              {eventName && (
                <span className="flex items-center gap-1 text-xs text-blue-600">
                  <Tag className="size-3" />
                  {eventName}
                </span>
              )}
            </Button>
            <div className="px-3 pb-1">
              <EventNameEditor
                threadId={t.thread_id}
                currentName={eventName}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ThreadHistoryLoading() {
  return (
    <div className="flex h-full w-full flex-col items-start justify-start gap-2 overflow-y-scroll [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-gray-300 [&::-webkit-scrollbar-track]:bg-transparent">
      {Array.from({ length: 30 }).map((_, i) => (
        <Skeleton
          key={`skeleton-${i}`}
          className="h-10 w-[280px]"
        />
      ))}
    </div>
  );
}

export default function ThreadHistory() {
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");
  const [chatHistoryOpen, setChatHistoryOpen] = useQueryState(
    "chatHistoryOpen",
    parseAsBoolean.withDefault(false),
  );

  const { getThreads, threads, setThreads, threadsLoading, setThreadsLoading } =
    useThreads();
  const { username, logout } = useAuth();

  useEffect(() => {
    if (typeof window === "undefined") return;
    setThreadsLoading(true);
    getThreads()
      .then(setThreads)
      .catch(console.error)
      .finally(() => setThreadsLoading(false));
  }, []);

  return (
    <>
      <div className="shadow-inner-right hidden h-screen w-[300px] shrink-0 flex-col items-start justify-start gap-4 border-r-[1px] border-slate-300 lg:flex">
        <div className="flex w-full items-center justify-between px-4 pt-1.5">
          <Button
            className="hover:bg-gray-100"
            variant="ghost"
            onClick={() => setChatHistoryOpen((p) => !p)}
          >
            {chatHistoryOpen ? (
              <PanelRightOpen className="size-5" />
            ) : (
              <PanelRightClose className="size-5" />
            )}
          </Button>
          <h1 className="text-xl font-semibold tracking-tight">
            Thread History
          </h1>
        </div>

        {/* User info + logout */}
        {username && (
          <div className="flex w-full items-center justify-between border-b px-4 pb-3">
            <span className="text-sm text-gray-600">
              Signed in as <strong>{username}</strong>
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={logout}
              className="h-7 gap-1 text-xs text-gray-500 hover:text-red-600"
            >
              <LogOut className="size-3" />
              Sign out
            </Button>
          </div>
        )}

        {threadsLoading ? (
          <ThreadHistoryLoading />
        ) : (
          <ThreadList threads={threads} />
        )}
      </div>
      <div className="lg:hidden">
        <Sheet
          open={!!chatHistoryOpen && !isLargeScreen}
          onOpenChange={(open) => {
            if (isLargeScreen) return;
            setChatHistoryOpen(open);
          }}
        >
          <SheetContent
            side="left"
            className="flex flex-col lg:hidden"
          >
            <SheetHeader>
              <SheetTitle>Thread History</SheetTitle>
            </SheetHeader>
            {username && (
              <div className="flex items-center justify-between border-b px-2 pb-2">
                <span className="text-sm text-gray-600">
                  <strong>{username}</strong>
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={logout}
                  className="h-7 gap-1 text-xs text-gray-500 hover:text-red-600"
                >
                  <LogOut className="size-3" />
                  Sign out
                </Button>
              </div>
            )}
            <ThreadList
              threads={threads}
              onThreadClick={() => setChatHistoryOpen((o) => !o)}
            />
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
