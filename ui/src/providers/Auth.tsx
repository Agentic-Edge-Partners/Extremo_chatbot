import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/ui/password-input";
import { ArrowRight } from "lucide-react";
import { APP_CONFIG } from "@/lib/app-config";

const AUTH_STORAGE_KEY = "ea:auth:username";

// ⚠️ PROTOTYPE ONLY — hardcoded credentials for demo/staging
// In production, replace with:
//   - AWS Cognito user pool authentication
//   - Or a backend API endpoint that validates credentials against a database
//   - Passwords should NEVER be stored in client-side code
const STAFF_ACCOUNTS: Record<string, string> = {
  admin: "extremo2024",
  pedro: "extremo2024",
  joana: "extremo2024",
  miguel: "extremo2024",
  ana: "extremo2024",
};

interface AuthContextType {
  username: string | null;
  login: (username: string, password: string) => boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return window.localStorage.getItem(AUTH_STORAGE_KEY);
    }
    return null;
  });

  const login = useCallback((user: string, password: string): boolean => {
    const normalizedUser = user.trim().toLowerCase();
    const expected = STAFF_ACCOUNTS[normalizedUser];
    if (expected && expected === password) {
      setUsername(normalizedUser);
      window.localStorage.setItem(AUTH_STORAGE_KEY, normalizedUser);
      return true;
    }
    return false;
  }, []);

  const logout = useCallback(() => {
    setUsername(null);
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }, []);

  return (
    <AuthContext.Provider value={{ username, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

// Login form component shown when user is not authenticated
export function LoginForm() {
  const { login } = useAuth();
  const [error, setError] = useState("");

  return (
    <div className="flex min-h-screen w-full items-center justify-center p-4">
      <div className="animate-in fade-in-0 zoom-in-95 bg-background flex w-full max-w-md flex-col rounded-lg border shadow-lg">
        <div className="mt-8 flex flex-col gap-2 border-b p-6">
          <div className="flex flex-col items-center gap-3">
            <img
              src="/logo.png"
              alt="Extremo Ambiente"
              className="h-12"
              style={{ objectFit: "contain" }}
            />
            <h1 className="text-xl font-semibold tracking-tight">
              {APP_CONFIG.name}
            </h1>
          </div>
          <p className="text-muted-foreground text-center text-sm">
            Sign in to access the corporate event planner
          </p>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setError("");
            const form = e.target as HTMLFormElement;
            const formData = new FormData(form);
            const user = formData.get("username") as string;
            const pass = formData.get("password") as string;

            if (!login(user, pass)) {
              setError("Invalid username or password");
              return;
            }
          }}
          className="bg-muted/50 flex flex-col gap-4 p-6"
        >
          <div className="flex flex-col gap-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              name="username"
              className="bg-background"
              placeholder="Enter your username"
              required
              autoFocus
            />
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="password">Password</Label>
            <PasswordInput
              id="password"
              name="password"
              className="bg-background"
              placeholder="Enter your password"
            />
          </div>

          {error && (
            <p className="text-sm text-red-500">{error}</p>
          )}

          <div className="mt-2 flex justify-end">
            <Button type="submit" size="lg">
              Sign In
              <ArrowRight className="size-5" />
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
