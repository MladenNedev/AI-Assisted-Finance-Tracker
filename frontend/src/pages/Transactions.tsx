import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Group,
  Modal,
  NumberInput,
  Pagination,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";

import { ApiError, apiFetch } from "../api/client";
import type {
  AccountResponse,
  CategoryResponse,
  CreateTransactionRequest,
  PaginatedResponse,
  TransactionDirection,
  TransactionResponse,
  UpdateTransactionRequest,
} from "../api/types";

const PAGE_LIMIT = 20;

type TransactionFormState = {
  account_id: string;
  amount: number | "";
  direction: TransactionDirection;
  category_id: string;
  merchant: string;
  note: string;
  occurred_at: string;
};

type TransactionFilters = {
  account_id: string;
  category_id: string;
  occurred_from: string;
  occurred_to: string;
};

const INITIAL_FILTERS: TransactionFilters = {
  account_id: "",
  category_id: "",
  occurred_from: "",
  occurred_to: "",
};

export default function Transactions() {
  const [transactions, setTransactions] = useState<TransactionResponse[]>([]);
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [opened, setOpened] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingTransaction, setEditingTransaction] = useState<TransactionResponse | null>(null);
  const [filters, setFilters] = useState<TransactionFilters>(INITIAL_FILTERS);
  const [filterInputs, setFilterInputs] = useState<TransactionFilters>(INITIAL_FILTERS);
  const [form, setForm] = useState<TransactionFormState>(emptyForm());

  const accountLookup = useMemo(
    () => new Map(accounts.map((account) => [account.id, account])),
    [accounts],
  );
  const categoryLookup = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories],
  );

  const accountOptions = useMemo(
    () =>
      accounts.map((account) => ({
        value: account.id,
        label: `${account.name} (${account.currency} ${account.current_balance})`,
      })),
    [accounts],
  );

  const filteredCategoryOptions = useMemo(
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
  }, []);

  useEffect(() => {
    void loadTransactions(page, filters);
  }, [page, filters]);

  const onOpenCreate = () => {
    setEditingTransaction(null);
    setForm(emptyForm(accounts[0]?.id));
    setOpened(true);
  };

  const onOpenEdit = (transaction: TransactionResponse) => {
    setEditingTransaction(transaction);
    setForm({
      account_id: transaction.account_id,
      amount: toNumber(transaction.amount),
      direction: transaction.direction,
      category_id: transaction.category_id ?? "",
      merchant: transaction.merchant ?? "",
      note: transaction.note ?? "",
      occurred_at: toDateTimeLocal(transaction.occurred_at),
    });
    setOpened(true);
  };

  const onSubmit = async () => {
    if (!form.account_id || form.amount === "" || form.amount <= 0 || !form.occurred_at) {
      setError("Account, amount, and date/time are required");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      if (editingTransaction) {
        const payload: UpdateTransactionRequest = {
          amount: Number(form.amount).toFixed(2),
          direction: form.direction,
          category_id: form.category_id || null,
          merchant: normalizeString(form.merchant),
          note: normalizeString(form.note),
          occurred_at: toIsoString(form.occurred_at),
        };
        await apiFetch<TransactionResponse>(`/transactions/${editingTransaction.id}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        const payload: CreateTransactionRequest = {
          account_id: form.account_id,
          amount: Number(form.amount).toFixed(2),
          direction: form.direction,
          category_id: form.category_id || null,
          merchant: normalizeString(form.merchant) ?? undefined,
          note: normalizeString(form.note) ?? undefined,
          occurred_at: toIsoString(form.occurred_at),
        };
        await apiFetch<TransactionResponse>("/transactions", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }

      setOpened(false);
      setEditingTransaction(null);
      setForm(emptyForm(accounts[0]?.id));
      await loadTransactions(page, filters);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const onDelete = async (transaction: TransactionResponse) => {
    const confirmed = window.confirm("Delete this transaction?");
    if (!confirmed) {
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await apiFetch<void>(`/transactions/${transaction.id}`, { method: "DELETE" });

      const nextTotal = total - 1;
      const maxPage = Math.max(1, Math.ceil(nextTotal / PAGE_LIMIT));
      const nextPage = page > maxPage ? maxPage : page;
      if (nextPage !== page) {
        setPage(nextPage);
      } else {
        await loadTransactions(page, filters);
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const onApplyFilters = () => {
    setPage(1);
    setFilters({ ...filterInputs });
  };

  const onResetFilters = () => {
    setPage(1);
    setFilterInputs(INITIAL_FILTERS);
    setFilters(INITIAL_FILTERS);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_LIMIT));

  return (
    <Stack mt="md" gap="md">
      <Group justify="space-between">
        <Title order={2}>Transactions</Title>
        <Group>
          <Text c="dimmed" size="sm">
            {total} total
          </Text>
          <Button onClick={onOpenCreate} disabled={!accounts.length}>
            Add transaction
          </Button>
        </Group>
      </Group>

      {error ? (
        <Alert color="red" title="Transaction request failed">
          {error}
        </Alert>
      ) : null}

      <Group align="end" wrap="wrap">
        <Select
          label="Account"
          placeholder="All accounts"
          clearable
          data={accountOptions}
          value={filterInputs.account_id || null}
          onChange={(value) =>
            setFilterInputs((current) => ({ ...current, account_id: value ?? "" }))
          }
          w={220}
        />
        <Select
          label="Category"
          placeholder="All categories"
          clearable
          data={categories.map((category) => ({
            value: category.id,
            label: category.icon ? `${category.icon} ${category.name}` : category.name,
          }))}
          value={filterInputs.category_id || null}
          onChange={(value) =>
            setFilterInputs((current) => ({ ...current, category_id: value ?? "" }))
          }
          w={220}
        />
        <TextInput
          label="From"
          type="date"
          value={filterInputs.occurred_from}
          onChange={(event) =>
            setFilterInputs((current) => ({
              ...current,
              occurred_from: event.currentTarget.value,
            }))
          }
        />
        <TextInput
          label="To"
          type="date"
          value={filterInputs.occurred_to}
          onChange={(event) =>
            setFilterInputs((current) => ({
              ...current,
              occurred_to: event.currentTarget.value,
            }))
          }
        />
        <Button variant="light" onClick={onApplyFilters}>
          Apply
        </Button>
        <Button variant="subtle" onClick={onResetFilters}>
          Reset
        </Button>
      </Group>

      <Table striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Date</Table.Th>
            <Table.Th>Description</Table.Th>
            <Table.Th>Category</Table.Th>
            <Table.Th>Account</Table.Th>
            <Table.Th ta="right">Amount</Table.Th>
            <Table.Th ta="right">Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {transactions.map((transaction) => {
            const account = accountLookup.get(transaction.account_id);
            const category = transaction.category_id
              ? categoryLookup.get(transaction.category_id)
              : null;

            return (
              <Table.Tr key={transaction.id}>
                <Table.Td>{formatDate(transaction.occurred_at)}</Table.Td>
                <Table.Td>
                  <Stack gap={0}>
                    <Text>{transaction.merchant ?? "No description"}</Text>
                    {transaction.note ? (
                      <Text size="xs" c="dimmed">
                        {transaction.note}
                      </Text>
                    ) : null}
                  </Stack>
                </Table.Td>
                <Table.Td>
                  {category ? (
                    <Badge color={category.color ?? "gray"}>
                      {category.icon ? `${category.icon} ` : ""}
                      {category.name}
                    </Badge>
                  ) : (
                    <Badge color="gray">Uncategorized</Badge>
                  )}
                </Table.Td>
                <Table.Td>{account?.name ?? "Unknown account"}</Table.Td>
                <Table.Td ta="right">
                  <Text c={transaction.direction === "IN" ? "teal" : "red"} fw={600}>
                    {transaction.direction === "IN" ? "+" : "-"}${transaction.amount}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Group justify="flex-end" gap="xs">
                    <Button size="xs" variant="subtle" onClick={() => onOpenEdit(transaction)}>
                      Edit
                    </Button>
                    <Button
                      size="xs"
                      variant="subtle"
                      color="red"
                      onClick={() => onDelete(transaction)}
                      loading={submitting}
                    >
                      Delete
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            );
          })}
          {!loading && transactions.length === 0 ? (
            <Table.Tr>
              <Table.Td colSpan={6}>
                <Text ta="center" c="dimmed">
                  No transactions found for current filters.
                </Text>
              </Table.Td>
            </Table.Tr>
          ) : null}
        </Table.Tbody>
      </Table>

      <Group justify="center">
        <Pagination value={page} onChange={setPage} total={totalPages} />
      </Group>

      <Modal
        opened={opened}
        onClose={() => setOpened(false)}
        title={editingTransaction ? "Edit transaction" : "Create transaction"}
        centered
        size="lg"
      >
        <Stack>
          <Select
            label="Account"
            data={accountOptions}
            value={form.account_id || null}
            onChange={(value) => setForm((current) => ({ ...current, account_id: value ?? "" }))}
            searchable
            disabled={editingTransaction !== null}
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
              data={[
                { value: "OUT", label: "Expense (OUT)" },
                { value: "IN", label: "Income (IN)" },
              ]}
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
            label="Category (optional)"
            placeholder="Uncategorized"
            data={filteredCategoryOptions}
            value={form.category_id || null}
            onChange={(value) => setForm((current) => ({ ...current, category_id: value ?? "" }))}
            clearable
            searchable
          />
          <TextInput
            label="Merchant / Description"
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
            label="Occurred at"
            type="datetime-local"
            value={form.occurred_at}
            onChange={(event) =>
              setForm((current) => ({ ...current, occurred_at: event.currentTarget.value }))
            }
            required
          />
          <Button onClick={onSubmit} loading={submitting}>
            {editingTransaction ? "Update transaction" : "Create transaction"}
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );

  async function loadReferenceData() {
    try {
      const [accountResponse, categoryResponse] = await Promise.all([
        apiFetch<PaginatedResponse<AccountResponse>>("/accounts?limit=500&offset=0"),
        apiFetch<PaginatedResponse<CategoryResponse>>("/categories?limit=500&offset=0"),
      ]);
      setAccounts(accountResponse.items);
      setCategories(categoryResponse.items);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }

  async function loadTransactions(targetPage: number, targetFilters: TransactionFilters) {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        limit: String(PAGE_LIMIT),
        offset: String((targetPage - 1) * PAGE_LIMIT),
      });
      if (targetFilters.account_id) {
        params.set("account_id", targetFilters.account_id);
      }
      if (targetFilters.category_id) {
        params.set("category_id", targetFilters.category_id);
      }
      if (targetFilters.occurred_from) {
        params.set("occurred_from", `${targetFilters.occurred_from}T00:00:00Z`);
      }
      if (targetFilters.occurred_to) {
        params.set("occurred_to", `${targetFilters.occurred_to}T23:59:59Z`);
      }

      const response = await apiFetch<PaginatedResponse<TransactionResponse>>(
        `/transactions?${params.toString()}`,
      );
      setTransactions(response.items);
      setTotal(response.total);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }
}

function emptyForm(defaultAccountId = ""): TransactionFormState {
  return {
    account_id: defaultAccountId,
    amount: "",
    direction: "OUT",
    category_id: "",
    merchant: "",
    note: "",
    occurred_at: toDateTimeLocal(new Date().toISOString()),
  };
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function toDateTimeLocal(isoDateString: string): string {
  const date = new Date(isoDateString);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const offsetMs = date.getTimezoneOffset() * 60 * 1000;
  const localDate = new Date(date.getTime() - offsetMs);
  return localDate.toISOString().slice(0, 16);
}

function toIsoString(dateTimeLocal: string): string {
  return new Date(dateTimeLocal).toISOString();
}

function normalizeString(value: string): string | null {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  return normalized;
}

function toNumber(value: string): number {
  const parsed = Number.parseFloat(value);
  if (Number.isNaN(parsed)) {
    return 0;
  }
  return parsed;
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
    return `Request failed (${error.status})`;
  }
  return "Unexpected error";
}
