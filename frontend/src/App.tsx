import { AppShell, Group, Text } from "@mantine/core";
import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";

function AppLayout() {
  const { user } = useAuth();

  return (
    <AppShell padding="md" header={{ height: 56 }}>
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" align="center">
          <Text fw={700}>Finance Tracker</Text>
          <Text size="sm" c="dimmed">
            {user ? user.email : "Not signed in"}
          </Text>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppLayout />
    </AuthProvider>
  );
}
