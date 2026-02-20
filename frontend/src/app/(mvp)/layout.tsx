import { AppConfigProvider } from "@/components/app-config-context";
import DashboardShell from "@/components/dashboard-shell-simple";
import ProtectedRoute from "@/components/ProtectedRoute";
import Navbar from "@/components/Navbar";

export default function MvpLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <AppConfigProvider>
        <div className="min-h-screen bg-gray-50">
          <Navbar />
          <DashboardShell>{children}</DashboardShell>
        </div>
      </AppConfigProvider>
    </ProtectedRoute>
  );
}
