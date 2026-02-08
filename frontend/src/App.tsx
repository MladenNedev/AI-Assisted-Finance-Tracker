import { AppShell, Button, Group, Text } from "@mantine/core";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Accounts from "./pages/Accounts";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";

function AppLayout() {
  const { user } = useAuth();
  const location = useLocation();

  return (
    <AppShell padding="md" header={{ height: 56 }}>
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="sm">
            <Text fw={700}>Finance Tracker</Text>
            {user ? (
              <Group gap="xs">
                <Button
                  component={Link}
                  to="/dashboard"
                  size="xs"
                  variant={location.pathname.startsWith("/dashboard") ? "light" : "subtle"}
                >
                  Dashboard
                </Button>
                <Button
                  component={Link}
                  to="/accounts"
                  size="xs"
                  variant={location.pathname.startsWith("/accounts") ? "light" : "subtle"}
                >
                  Accounts
                </Button>
              </Group>
            ) : null}
          </Group>
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
          <Route
            path="/accounts"
            element={
              <ProtectedRoute>
                <Accounts />
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
