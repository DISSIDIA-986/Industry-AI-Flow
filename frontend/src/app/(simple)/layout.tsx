import { AppConfigProvider } from "@/components/app-config-context";
import ProtectedRoute from "@/components/ProtectedRoute";
import Navbar from "@/components/Navbar";

export default function SimpleLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <AppConfigProvider>
        <div className="min-h-screen bg-gray-50">
          <Navbar />
          <main className="pt-6">
            {children}
          </main>
        </div>
      </AppConfigProvider>
    </ProtectedRoute>
  );
}