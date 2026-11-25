import { Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./AuthContext";
import CountersPage from "./CountersPage";
import LoginPage from "./LoginPage";
import OverviewPage from "./OverviewPage";
import QueuePage from "./QueuePage";
import StaffLayout from "./StaffLayout";

function ProtectedRoutes() {
  const { token } = useAuth();
  if (!token) return <LoginPage />;

  return (
    <StaffLayout>
      <Routes>
        <Route path="overview" element={<OverviewPage />} />
        <Route path="queue" element={<QueuePage />} />
        <Route path="counters" element={<CountersPage />} />
        <Route path="*" element={<Navigate to="overview" replace />} />
      </Routes>
    </StaffLayout>
  );
}

export default function StaffApp() {
  return (
    <AuthProvider>
      <ProtectedRoutes />
    </AuthProvider>
  );
}
