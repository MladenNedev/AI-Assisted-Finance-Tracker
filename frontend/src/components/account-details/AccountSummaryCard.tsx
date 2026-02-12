import { Card, Group, Progress, Stack, Text } from "@mantine/core";

import type { AccountResponse } from "../../api/types";

type AccountSummaryCardProps = {
  account: AccountResponse | null;
};

export default function AccountSummaryCard({ account }: AccountSummaryCardProps) {
  if (!account) {
    return null;
  }

  const goalTarget = account.goal_target_amount
    ? Number(account.goal_target_amount)
    : null;
  const currentBalance = Number(account.current_balance);
  const goalProgress = goalTarget
    ? Math.min(100, (currentBalance / goalTarget) * 100)
    : 0;

  return (
    <Card withBorder radius="md" p="lg">
      <Group justify="space-between" align="center">
        <div>
          <Group gap="xs">
            {account.color ? (
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  backgroundColor: account.color,
                }}
              />
            ) : null}
            {account.icon ? <Text>{account.icon}</Text> : null}
            <Text fw={600}>{account.name}</Text>
          </Group>
          <Text size="sm" c="dimmed">
            {account.account_type} · {account.currency}
          </Text>
        </div>
        <div>
          <Text size="sm" c="dimmed">
            Opening balance
          </Text>
          <Text fw={600}>
            {account.currency} {account.opening_balance}
          </Text>
        </div>
        <div>
          <Text size="sm" c="dimmed">
            Current balance
          </Text>
          <Text fw={600}>
            {account.currency} {account.current_balance}
          </Text>
        </div>
        <div>
          <Text size="sm" c="dimmed">
            Goal
          </Text>
          {goalTarget ? (
            <Stack gap={4}>
              <Text fw={600}>${goalTarget.toFixed(2)}</Text>
              <Progress value={goalProgress} size="sm" />
            </Stack>
          ) : (
            <Text c="dimmed">No goal</Text>
          )}
        </div>
      </Group>
    </Card>
  );
}
