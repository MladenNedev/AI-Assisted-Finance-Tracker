import { useState } from "react";
import { AppShell, Button, Group, Text } from "@mantine/core";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";

export default function App() {
  const [view, setView] = useState<"login" | "dashboard">("login");

  return (
    <AppShell padding="md" header={{ height: 56 }}>
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Text fw={700}>Finance Tracker</Text>
          <Group>
            <Button
              variant={view === "login" ? "filled" : "light"}
              size="xs"
              onClick={() => setView("login")}
            >
              Login
            </Button>
            <Button
              variant={view === "dashboard" ? "filled" : "light"}
              size="xs"
              onClick={() => setView("dashboard")}
            >
              Dashboard
            </Button>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        {view === "login" ? (
          <Login onSuccess={() => setView("dashboard")} />
        ) : (
          <Dashboard />
        )}
      </AppShell.Main>
    </AppShell>
  );
}
