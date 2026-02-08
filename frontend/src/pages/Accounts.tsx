import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title
} from "@mantine/core";
import { ApiError, apiFetch } from "../api/client";
import type {
  AccountResponse,
  AccountType,
  CreateAccountRequest,
  PaginatedResponse
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
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<CreateAccountRequest>({
    name: "",
    account_type: "CHECKING",
    opening_balance: "0.00",
    currency: "USD"
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
      await apiFetch<AccountResponse>("/accounts", {
        method: "POST",
        body: JSON.stringify(form)
      });
      setOpened(false);
      setForm({
        name: "",
        account_type: "CHECKING",
        opening_balance: "0.00",
        currency: "USD"
      });
      await loadAccounts();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Stack mt="md" gap="md">
      <Group justify="space-between">
        <Title order={2}>Accounts</Title>
        <Group>
          <Text c="dimmed" size="sm">
            {total} total
          </Text>
          <Button onClick={() => setOpened(true)}>Add account</Button>
        </Group>
      </Group>

      {error ? (
        <Alert color="red" title="Request failed">
          {error}
        </Alert>
      ) : null}

      <Table striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Type</Table.Th>
            <Table.Th>Currency</Table.Th>
            <Table.Th ta="right">Opening</Table.Th>
            <Table.Th ta="right">Current</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {accounts.map((account) => (
            <Table.Tr key={account.id}>
              <Table.Td>{account.name}</Table.Td>
              <Table.Td>{account.account_type}</Table.Td>
              <Table.Td>{account.currency}</Table.Td>
              <Table.Td ta="right">{account.opening_balance}</Table.Td>
              <Table.Td ta="right">{account.current_balance}</Table.Td>
            </Table.Tr>
          ))}
          {!loading && accounts.length === 0 ? (
            <Table.Tr>
              <Table.Td colSpan={5}>
                <Text c="dimmed" ta="center">
                  No accounts yet.
                </Text>
              </Table.Td>
            </Table.Tr>
          ) : null}
        </Table.Tbody>
      </Table>

      <Modal
        opened={opened}
        onClose={() => setOpened(false)}
        title="Create account"
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
          <Button loading={submitting} onClick={onCreateAccount}>
            Create
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );
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
