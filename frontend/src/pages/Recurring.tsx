import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";

import { ApiError, apiFetch } from "../api/client";
import type {
  AccountResponse,
  CategoryResponse,
  PaginatedResponse,
  RecurringCadence,
  RecurringRunResponse,
  RecurringTransactionCreateRequest,
  RecurringTransactionListResponse,
  RecurringTransactionResponse,
  RecurringTransactionUpdateRequest,
  TransactionDirection,
} from "../api/types";

const CADENCE_OPTIONS: RecurringCadence[] = ["DAILY", "WEEKLY", "MONTHLY"];
const DIRECTION_OPTIONS: TransactionDirection[] = ["OUT", "IN"];

type RecurringFormState = {
  account_id: string;
  category_id: string;
  amount: number | "";
  direction: TransactionDirection;
  cadence: RecurringCadence;
  interval: number | "";
  start_at: string;
  end_at: string;
  merchant: string;
  note: string;
  tags: string;
  is_active: boolean;
};

const emptyForm = (accountId = ""): RecurringFormState => ({
  account_id: accountId,
  category_id: "",
  amount: "",
  direction: "OUT",
  cadence: "MONTHLY",
  interval: 1,
  start_at: toDateTimeLocal(new Date().toISOString()),
  end_at: "",
  merchant: "",
  note: "",
  tags: "",
  is_active: true,
});

export default function Recurring() {
  const [recurring, setRecurring] = useState<RecurringTransactionResponse[]>([]);
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [opened, setOpened] = useState(false);
  const [editing, setEditing] = useState<RecurringTransactionResponse | null>(null);
  const [form, setForm] = useState<RecurringFormState>(emptyForm());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<RecurringRunResponse | null>(null);

  const accountOptions = useMemo(
    () =>
      accounts.map((account) => ({
        value: account.id,
        label: `${account.name} (${account.currency} ${account.current_balance})`,
      })),
    [accounts],
  );

  const categoryOptions = useMemo(
    () =>
      categories
        .filter((category) => category.is_income === (form.direction === "IN"))
        .map((category) => ({
          value: category.id,
          label: category.icon ? `${category.icon} ${category.name}` : category.name,
        })),
    [categories, form.direction],
  );

  useEffect(() => {
    void loadReferenceData();
    void loadRecurring();
  }, []);

  const loadReferenceData = async () => {
    try {
      const [accountResponse, categoryResponse] = await Promise.all([
        apiFetch<PaginatedResponse<AccountResponse>>("/accounts"),
        apiFetch<PaginatedResponse<CategoryResponse>>("/categories"),
      ]);
      setAccounts(accountResponse.items);
      setCategories(categoryResponse.items);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  };

  const loadRecurring = async () => {
    setLoading(true);
    try {
      const response = await apiFetch<RecurringTransactionListResponse>(
        "/recurring?active_only=false",
      );
      setRecurring(response.items);
      setError(null);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  };

  const onOpenCreate = () => {
    setEditing(null);
    setForm(emptyForm(accounts[0]?.id));
    setOpened(true);
  };

  const onOpenEdit = (entry: RecurringTransactionResponse) => {
    setEditing(entry);
    setForm({
      account_id: entry.account_id,
      category_id: entry.category_id ?? "",
      amount: Number(entry.amount),
      direction: entry.direction,
      cadence: entry.cadence,
      interval: entry.interval,
      start_at: toDateTimeLocal(entry.start_at),
      end_at: entry.end_at ? toDateTimeLocal(entry.end_at) : "",
      merchant: entry.merchant ?? "",
      note: entry.note ?? "",
      tags: (entry.tags ?? []).join(", "),
      is_active: entry.is_active,
    });
    setOpened(true);
  };

  const onSubmit = async () => {
    if (!form.account_id || form.amount === "" || form.amount <= 0) {
      setError("Account and amount are required");
      return;
    }
    if (!form.start_at) {
      setError("Start date is required");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      if (editing) {
        const payload: RecurringTransactionUpdateRequest = {
          category_id: form.category_id || null,
          amount: Number(form.amount).toFixed(2),
          direction: form.direction,
          cadence: form.cadence,
          interval: form.interval === "" ? undefined : Number(form.interval),
          start_at: toIsoString(form.start_at),
          end_at: form.end_at ? toIsoString(form.end_at) : null,
          merchant: normalizeString(form.merchant) ?? null,
          note: normalizeString(form.note) ?? null,
          tags: parseTagsInput(form.tags),
          is_active: form.is_active,
        };
        await apiFetch(`/recurring/${editing.id}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        const payload: RecurringTransactionCreateRequest = {
          account_id: form.account_id,
          category_id: form.category_id || null,
          amount: Number(form.amount).toFixed(2),
          direction: form.direction,
          cadence: form.cadence,
          interval: form.interval === "" ? 1 : Number(form.interval),
          start_at: toIsoString(form.start_at),
          end_at: form.end_at ? toIsoString(form.end_at) : null,
          merchant: normalizeString(form.merchant) ?? null,
          note: normalizeString(form.note) ?? null,
          tags: parseTagsInput(form.tags),
        };
        await apiFetch("/recurring", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }

      setOpened(false);
      setEditing(null);
      setForm(emptyForm(accounts[0]?.id));
      await loadRecurring();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const onDelete = async (entry: RecurringTransactionResponse) => {
    const confirmed = window.confirm("Delete this recurring schedule?");
    if (!confirmed) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await apiFetch(`/recurring/${entry.id}`, { method: "DELETE" });
      await loadRecurring();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const onRunNow = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const response = await apiFetch<RecurringRunResponse>("/recurring/run", {
        method: "POST",
      });
      setRunResult(response);
      await loadRecurring();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Stack mt="md" gap="md">
      <Group justify="space-between">
        <Title order={2}>Recurring transactions</Title>
        <Group>
          <Button variant="light" onClick={onRunNow} loading={submitting}>
            Run due now
          </Button>
          <Button onClick={onOpenCreate}>Add recurring</Button>
        </Group>
      </Group>

      {error ? (
        <Alert color="red" title="Recurring request failed">
          {error}
        </Alert>
      ) : null}

      {runResult ? (
        <Alert color="teal" title="Recurring run completed">
          Created {runResult.created} transactions, skipped {runResult.skipped}.
        </Alert>
      ) : null}

      <Table striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Account</Table.Th>
            <Table.Th>Amount</Table.Th>
            <Table.Th>Cadence</Table.Th>
            <Table.Th>Next run</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th ta="right">Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {recurring.map((entry) => {
            const account = accounts.find((item) => item.id === entry.account_id);
            return (
              <Table.Tr key={entry.id}>
                <Table.Td>{account?.name ?? "Unknown account"}</Table.Td>
                <Table.Td>
                  {entry.direction === "IN" ? "+" : "-"}${entry.amount}
                </Table.Td>
                <Table.Td>
                  {entry.cadence} x{entry.interval}
                </Table.Td>
                <Table.Td>{formatDateTime(entry.next_run_at)}</Table.Td>
                <Table.Td>{entry.is_active ? "Active" : "Paused"}</Table.Td>
                <Table.Td>
                  <Group justify="flex-end" gap="xs">
                    <Button size="xs" variant="subtle" onClick={() => onOpenEdit(entry)}>
                      Edit
                    </Button>
                    <Button
                      size="xs"
                      variant="subtle"
                      color="red"
                      onClick={() => onDelete(entry)}
                    >
                      Delete
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            );
          })}
          {!loading && recurring.length === 0 ? (
            <Table.Tr>
              <Table.Td colSpan={6}>
                <Text ta="center" c="dimmed">
                  No recurring transactions configured yet.
                </Text>
              </Table.Td>
            </Table.Tr>
          ) : null}
        </Table.Tbody>
      </Table>

      <Modal
        opened={opened}
        onClose={() => setOpened(false)}
        title={editing ? "Edit recurring" : "Create recurring"}
        centered
        size="lg"
      >
        <Stack>
          <Select
            label="Account"
            data={accountOptions}
            value={form.account_id || null}
            onChange={(value) =>
              setForm((current) => ({ ...current, account_id: value ?? "" }))
            }
            searchable
            disabled={editing !== null}
            required
          />
          <Group grow>
            <NumberInput
              label="Amount"
              value={form.amount}
              onChange={(value) => setForm((current) => ({ ...current, amount: value }))}
              min={0}
              decimalScale={2}
              fixedDecimalScale
              prefix="$"
              required
            />
            <Select
              label="Direction"
              data={DIRECTION_OPTIONS.map((value) => ({
                value,
                label: value === "IN" ? "Income" : "Expense",
              }))}
              value={form.direction}
              onChange={(value) =>
                setForm((current) => ({
                  ...current,
                  direction: (value as TransactionDirection | null) ?? "OUT",
                  category_id: "",
                }))
              }
            />
          </Group>
          <Select
            label="Category"
            placeholder="Uncategorized"
            data={categoryOptions}
            value={form.category_id || null}
            onChange={(value) =>
              setForm((current) => ({ ...current, category_id: value ?? "" }))
            }
            clearable
            searchable
          />
          <Group grow>
            <Select
              label="Cadence"
              data={CADENCE_OPTIONS.map((value) => ({ value, label: value }))}
              value={form.cadence}
              onChange={(value) =>
                setForm((current) => ({
                  ...current,
                  cadence: (value as RecurringCadence | null) ?? "MONTHLY",
                }))
              }
            />
            <NumberInput
              label="Interval"
              value={form.interval}
              onChange={(value) => setForm((current) => ({ ...current, interval: value }))}
              min={1}
            />
          </Group>
          <TextInput
            label="Start at"
            type="datetime-local"
            value={form.start_at}
            onChange={(event) =>
              setForm((current) => ({ ...current, start_at: event.currentTarget.value }))
            }
            required
          />
          <TextInput
            label="End at (optional)"
            type="datetime-local"
            value={form.end_at}
            onChange={(event) =>
              setForm((current) => ({ ...current, end_at: event.currentTarget.value }))
            }
          />
          <TextInput
            label="Merchant"
            value={form.merchant}
            onChange={(event) =>
              setForm((current) => ({ ...current, merchant: event.currentTarget.value }))
            }
          />
          <TextInput
            label="Note"
            value={form.note}
            onChange={(event) =>
              setForm((current) => ({ ...current, note: event.currentTarget.value }))
            }
          />
          <TextInput
            label="Tags"
            placeholder="comma, separated"
            value={form.tags}
            onChange={(event) =>
              setForm((current) => ({ ...current, tags: event.currentTarget.value }))
            }
          />
          {editing ? (
            <Switch
              label="Active"
              checked={form.is_active}
              onChange={(event) =>
                setForm((current) => ({ ...current, is_active: event.currentTarget.checked }))
              }
            />
          ) : null}
          <Button onClick={onSubmit} loading={submitting}>
            {editing ? "Update recurring" : "Create recurring"}
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );
}

function toIsoString(value: string) {
  if (!value) {
    return "";
  }
  return new Date(value).toISOString();
}

function toDateTimeLocal(value: string) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  const pad = (num: number) => String(num).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate(),
  )}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatDateTime(value: string) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString();
}

function normalizeString(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function parseTagsInput(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return trimmed
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong";
}
