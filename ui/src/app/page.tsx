"use client";

import { Thread } from "@/components/thread";
import { StreamProvider } from "@/providers/Stream";
import { ThreadProvider } from "@/providers/Thread";
import { AuthProvider, useAuth, LoginForm } from "@/providers/Auth";
import { ArtifactProvider } from "@/components/thread/artifact";
import { Toaster } from "@/components/ui/sonner";
import React from "react";

function AuthenticatedApp() {
  const { username } = useAuth();

  if (!username) {
    return <LoginForm />;
  }

  return (
    <ThreadProvider>
      <StreamProvider>
        <ArtifactProvider>
          <Thread />
        </ArtifactProvider>
      </StreamProvider>
    </ThreadProvider>
  );
}

export default function DemoPage(): React.ReactNode {
  return (
    <React.Suspense fallback={<div>Loading (layout)...</div>}>
      <Toaster />
      <AuthProvider>
        <AuthenticatedApp />
      </AuthProvider>
    </React.Suspense>
  );
}
