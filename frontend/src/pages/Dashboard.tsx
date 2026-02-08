import { Button, Card, Group, Stack, Text, Title } from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <Stack mt="md">
      <Group justify="space-between">
        <Title order={2}>Dashboard</Title>
        <Button variant="light" onClick={onLogout}>
          Logout
        </Button>
      </Group>
      <Card withBorder radius="md" p="lg">
        <Text size="sm">Signed in as {user?.email}</Text>
        <Text c="dimmed">
          Placeholder for reporting, budgets, and ledger summaries.
        </Text>
      </Card>
    </Stack>
  );
}
