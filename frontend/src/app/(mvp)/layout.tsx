import { AppConfigProvider } from "@/components/app-config-context";
import { DashboardShell } from "@/components/dashboard-shell";

export default function MvpLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppConfigProvider>
      <DashboardShell>{children}</DashboardShell>
    </AppConfigProvider>
  );
}
