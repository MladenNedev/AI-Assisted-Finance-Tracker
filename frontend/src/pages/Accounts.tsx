import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  ColorInput,
  Group,
  Modal,
  NumberInput,
  Progress,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title
} from "@mantine/core";
import { Link } from "react-router-dom";
import { ApiError, apiFetch } from "../api/client";
import ResponsiveTable from "../components/ResponsiveTable";
import type {
  AccountResponse,
  AccountType,
  CreateAccountRequest,
  PaginatedResponse,
  UpdateAccountRequest
} from "../api/types";

const ACCOUNT_TYPE_OPTIONS: AccountType[] = [
  "CHECKING",
  "SAVINGS",
  "CREDIT_CARD",
  "CASH",
  "INVESTMENT"
];

export default function Accounts() {
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [opened, setOpened] = useState(false);
  const [editing, setEditing] = useState<AccountResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<CreateAccountRequest>({
    name: "",
    account_type: "CHECKING",
    opening_balance: "0.00",
    currency: "USD",
    color: null,
    icon: null,
    goal_name: null,
    goal_target_amount: null,
    goal_target_date: null
  });

  const loadAccounts = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<PaginatedResponse<AccountResponse>>("/accounts");
      setAccounts(data.items);
      setTotal(data.total);
      setError(null);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAccounts();
  }, []);

  const onCreateAccount = async () => {
    setSubmitting(true);
    try {
      if (editing) {
        const payload: UpdateAccountRequest = {
          name: form.name,
          account_type: form.account_type,
          currency: form.currency,
          color: form.color ?? null,
          icon: form.icon ?? null,
          goal_name: form.goal_name ?? null,
          goal_target_amount: form.goal_target_amount ?? null,
          goal_target_date: form.goal_target_date ?? null
        };
        await apiFetch<AccountResponse>(`/accounts/${editing.id}`, {
          method: "PATCH",
          body: JSON.stringify(payload)
        });
      } else {
        await apiFetch<AccountResponse>("/accounts", {
          method: "POST",
          body: JSON.stringify(form)
        });
      }
      setOpened(false);
      setEditing(null);
      setForm(emptyForm());
      await loadAccounts();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const onOpenCreate = () => {
    setEditing(null);
    setForm(emptyForm());
    setOpened(true);
  };

  const onOpenEdit = (account: AccountResponse) => {
    setEditing(account);
    setForm({
      name: account.name,
      account_type: account.account_type,
      opening_balance: account.opening_balance,
      currency: account.currency,
      color: account.color,
      icon: account.icon,
      goal_name: account.goal_name,
      goal_target_amount: account.goal_target_amount,
      goal_target_date: account.goal_target_date
    });
    setOpened(true);
  };

  return (
    <Stack mt="md" gap="md">
      <Group justify="space-between">
        <Title order={2}>Accounts</Title>
        <Group>
          <Text c="dimmed" size="sm">
            {total} total
          </Text>
          <Button onClick={onOpenCreate}>Add account</Button>
        </Group>
      </Group>

      {error ? (
        <Alert color="red" title="Request failed">
          {error}
        </Alert>
      ) : null}

      <ResponsiveTable minWidth={880}>
        <Table striped highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Currency</Table.Th>
              <Table.Th>Goal</Table.Th>
              <Table.Th ta="right">Opening</Table.Th>
              <Table.Th ta="right">Current</Table.Th>
              <Table.Th ta="right">Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {accounts.map((account) => {
              const goalTarget = account.goal_target_amount
                ? Number.parseFloat(account.goal_target_amount)
                : null;
              const current = Number.parseFloat(account.current_balance || "0");
              const goalPercent =
                goalTarget && goalTarget > 0
                  ? Math.min(100, (current / goalTarget) * 100)
                  : null;
              return (
                <Table.Tr key={account.id}>
                  <Table.Td>
                    <Group gap="xs">
                      {account.color ? (
                        <div
                          style={{
                            width: 10,
                            height: 10,
                            borderRadius: "50%",
                            backgroundColor: account.color
                          }}
                        />
                      ) : null}
                      {account.icon ? <Text>{account.icon}</Text> : null}
                      <Text>{account.name}</Text>
                    </Group>
                  </Table.Td>
                  <Table.Td>{account.account_type}</Table.Td>
                  <Table.Td>{account.currency}</Table.Td>
                  <Table.Td>
                    {goalTarget ? (
                      <Stack gap={4}>
                        <Text size="xs" c="dimmed">
                          {account.goal_name ? account.goal_name : "Goal"} · $
                          {goalTarget.toFixed(2)}
                        </Text>
                        <Progress value={goalPercent ?? 0} size="sm" />
                      </Stack>
                    ) : (
                      <Text size="xs" c="dimmed">
                        No goal
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td ta="right">{account.opening_balance}</Table.Td>
                  <Table.Td ta="right">{account.current_balance}</Table.Td>
                  <Table.Td ta="right">
                    <Button
                      component={Link}
                      to={`/accounts/${account.id}`}
                      size="xs"
                      variant="subtle"
                    >
                      View
                    </Button>
                    <Button
                      size="xs"
                      variant="subtle"
                      onClick={() => onOpenEdit(account)}
                    >
                      Edit
                    </Button>
                  </Table.Td>
                </Table.Tr>
              );
            })}
            {!loading && accounts.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={7}>
                  <Text c="dimmed" ta="center">
                    No accounts yet.
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : null}
          </Table.Tbody>
        </Table>
      </ResponsiveTable>

      <Modal
        opened={opened}
        onClose={() => setOpened(false)}
        title={editing ? "Edit account" : "Create account"}
        centered
      >
        <Stack>
          <TextInput
            label="Name"
            placeholder="Primary checking"
            value={form.name}
            onChange={(event) =>
              setForm((current) => ({ ...current, name: event.currentTarget.value }))
            }
          />
          <Select
            label="Account type"
            data={ACCOUNT_TYPE_OPTIONS}
            value={form.account_type}
            onChange={(value) =>
              setForm((current) => ({
                ...current,
                account_type: (value as AccountType | null) ?? "CHECKING"
              }))
            }
          />
          <TextInput
            label="Opening balance"
            value={form.opening_balance}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                opening_balance: event.currentTarget.value
              }))
            }
          />
          <TextInput
            label="Currency"
            value={form.currency}
            maxLength={3}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                currency: event.currentTarget.value.toUpperCase()
              }))
            }
          />
          <Group grow>
            <TextInput
              label="Icon"
              placeholder="💳"
              value={form.icon ?? ""}
              onChange={(event) =>
                setForm((current) => ({ ...current, icon: event.currentTarget.value }))
              }
            />
            <ColorInput
              label="Color"
              placeholder="#1A2B3C"
              value={form.color ?? ""}
              onChange={(value) => setForm((current) => ({ ...current, color: value }))}
            />
          </Group>
          <TextInput
            label="Goal name"
            placeholder="New laptop"
            value={form.goal_name ?? ""}
            onChange={(event) =>
              setForm((current) => ({ ...current, goal_name: event.currentTarget.value }))
            }
          />
          <Group grow>
            <NumberInput
              label="Goal target amount"
              value={form.goal_target_amount ? Number(form.goal_target_amount) : ""}
              onChange={(value) =>
                setForm((current) => ({
                  ...current,
                  goal_target_amount:
                    value === "" || value === null ? null : Number(value).toFixed(2)
                }))
              }
              min={0}
              decimalScale={2}
              prefix="$"
            />
            <TextInput
              label="Goal target date"
              type="date"
              value={form.goal_target_date ?? ""}
              onChange={(event) =>
                setForm((current) => ({ ...current, goal_target_date: event.currentTarget.value }))
              }
            />
          </Group>
          <Button loading={submitting} onClick={onCreateAccount}>
            {editing ? "Update" : "Create"}
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );
}

function emptyForm(): CreateAccountRequest {
  return {
    name: "",
    account_type: "CHECKING",
    opening_balance: "0.00",
    currency: "USD",
    color: null,
    icon: null,
    goal_name: null,
    goal_target_amount: null,
    goal_target_date: null
  };
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const payload = error.payload as { message?: string } | string | undefined;
    if (typeof payload === "string") {
      return payload;
    }
    if (payload && typeof payload.message === "string") {
      return payload.message;
    }
  }
  return "Unexpected error";
}
