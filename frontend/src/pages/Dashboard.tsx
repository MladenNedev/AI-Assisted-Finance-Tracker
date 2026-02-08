import { Card, Stack, Text, Title } from "@mantine/core";

export default function Dashboard() {
  return (
    <Stack mt="md">
      <Title order={2}>Dashboard</Title>
      <Card withBorder radius="md" p="lg">
        <Text c="dimmed">
          Placeholder for reporting, budgets, and ledger summaries.
        </Text>
      </Card>
    </Stack>
  );
}
