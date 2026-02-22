"use client";

import { useSession } from "next-auth/react";
import { createContext, useContext, useEffect, useState } from "react";
import { apiClient } from "@/lib/api-client";

interface AuthContextType {
  isReady: boolean;
}

const AuthContext = createContext<AuthContextType>({ isReady: false });

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (status === "authenticated" && session) {
      const backendToken = (session as any).backendToken;
      if (backendToken) {
        apiClient.setToken(backendToken);
        setIsReady(true);
      }
    } else if (status === "unauthenticated") {
      setIsReady(false);
    }
  }, [session, status]);

  return (
    <AuthContext.Provider value={{ isReady }}>{children}</AuthContext.Provider>
  );
}
