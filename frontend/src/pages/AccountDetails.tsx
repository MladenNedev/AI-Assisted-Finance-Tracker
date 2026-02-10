import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Group,
  Pagination,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { Link, useParams } from "react-router-dom";

import { ApiError, apiFetch } from "../api/client";
import type {
  AccountResponse,
  CategoryResponse,
  PaginatedResponse,
  TransactionResponse,
} from "../api/types";

const PAGE_LIMIT = 20;

export default function AccountDetails() {
  const { accountId } = useParams();
  const [account, setAccount] = useState<AccountResponse | null>(null);
  const [transactions, setTransactions] = useState<TransactionResponse[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const categoryLookup = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories],
  );

  useEffect(() => {
    if (!accountId) {
      setError("Account id missing from route");
      return;
    }
    void loadAccount(accountId);
    void loadCategories();
  }, [accountId]);

  useEffect(() => {
    if (!accountId) {
      return;
    }
    void loadTransactions(accountId, page);
  }, [accountId, page]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_LIMIT));

  return (
    <Stack mt="md" gap="md">
      <Group justify="space-between" align="center">
        <Title order={2}>Account Details</Title>
        <Button component={Link} to="/accounts" variant="subtle">
          Back to accounts
        </Button>
      </Group>

      {error ? (
        <Alert color="red" title="Failed to load account">
          {error}
        </Alert>
      ) : null}

      {account ? (
        <Card withBorder radius="md" p="lg">
          <Group justify="space-between">
            <div>
              <Text fw={600}>{account.name}</Text>
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
          </Group>
        </Card>
      ) : null}

      <Table striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Date</Table.Th>
            <Table.Th>Description</Table.Th>
            <Table.Th>Category</Table.Th>
            <Table.Th ta="right">Amount</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {transactions.map((transaction) => {
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
                    <Text>{category.icon ? `${category.icon} ` : ""}{category.name}</Text>
                  ) : (
                    <Text c="dimmed">Uncategorized</Text>
                  )}
                </Table.Td>
                <Table.Td ta="right">
                  <Text c={transaction.direction === "IN" ? "teal" : "red"} fw={600}>
                    {transaction.direction === "IN" ? "+" : "-"}${transaction.amount}
                  </Text>
                </Table.Td>
              </Table.Tr>
            );
          })}
          {!loading && transactions.length === 0 ? (
            <Table.Tr>
              <Table.Td colSpan={4}>
                <Text c="dimmed" ta="center">
                  No transactions for this account yet.
                </Text>
              </Table.Td>
            </Table.Tr>
          ) : null}
        </Table.Tbody>
      </Table>

      <Group justify="center">
        <Pagination value={page} onChange={setPage} total={totalPages} />
      </Group>
    </Stack>
  );

  async function loadAccount(id: string) {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch<AccountResponse>(`/accounts/${id}`);
      setAccount(response);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function loadTransactions(id: string, targetPage: number) {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        account_id: id,
        limit: String(PAGE_LIMIT),
        offset: String((targetPage - 1) * PAGE_LIMIT),
      });
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

  async function loadCategories() {
    try {
      const response = await apiFetch<PaginatedResponse<CategoryResponse>>(
        "/categories?limit=500&offset=0",
      );
      setCategories(response.items);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    }
  }
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
