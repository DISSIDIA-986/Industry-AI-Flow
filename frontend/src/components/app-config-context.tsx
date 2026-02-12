"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type RouteMode = "local_only" | "hybrid_auto" | "cloud_only";

export interface AppConfigState {
  apiKey: string;
  tenantId: string;
  userId: string;
  routeMode: RouteMode;
}

interface AppConfigContextValue {
  config: AppConfigState;
  setApiKey: (value: string) => void;
  setTenantId: (value: string) => void;
  setUserId: (value: string) => void;
  setRouteMode: (value: RouteMode) => void;
}

const STORAGE_KEY = "industry-aiflow-mvp-config";

const defaultConfig: AppConfigState = {
  apiKey: "",
  tenantId: "capstone-demo",
  userId: "demo-user",
  routeMode: "hybrid_auto",
};

const AppConfigContext = createContext<AppConfigContextValue | undefined>(undefined);

function readStoredConfig(): AppConfigState {
  if (typeof window === "undefined") {
    return defaultConfig;
  }

  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return defaultConfig;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<AppConfigState>;
    return {
      apiKey: parsed.apiKey ?? defaultConfig.apiKey,
      tenantId: parsed.tenantId ?? defaultConfig.tenantId,
      userId: parsed.userId ?? defaultConfig.userId,
      routeMode: parsed.routeMode ?? defaultConfig.routeMode,
    };
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return defaultConfig;
  }
}

export function AppConfigProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<AppConfigState>(readStoredConfig);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  }, [config]);

  const setApiKey = useCallback((value: string) => {
    setConfig((prev) => ({ ...prev, apiKey: value }));
  }, []);

  const setTenantId = useCallback((value: string) => {
    setConfig((prev) => ({ ...prev, tenantId: value.trim() || defaultConfig.tenantId }));
  }, []);

  const setUserId = useCallback((value: string) => {
    setConfig((prev) => ({ ...prev, userId: value.trim() || defaultConfig.userId }));
  }, []);

  const setRouteMode = useCallback((value: RouteMode) => {
    setConfig((prev) => ({ ...prev, routeMode: value }));
  }, []);

  const value = useMemo(
    () => ({ config, setApiKey, setTenantId, setUserId, setRouteMode }),
    [config, setApiKey, setTenantId, setUserId, setRouteMode],
  );

  return <AppConfigContext.Provider value={value}>{children}</AppConfigContext.Provider>;
}

export function useAppConfig() {
  const ctx = useContext(AppConfigContext);
  if (!ctx) {
    throw new Error("useAppConfig must be used within AppConfigProvider");
  }
  return ctx;
}
