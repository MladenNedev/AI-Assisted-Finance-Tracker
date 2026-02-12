import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import {
  Alert,
  ActionIcon,
  Badge,
  Button,
  Checkbox,
  Divider,
  FileInput,
  Group,
  Modal,
  NumberInput,
  Pagination,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";

import { API_BASE_URL, ApiError, apiFetch, getCsrfToken } from "../api/client";
import ResponsiveTable from "../components/ResponsiveTable";
import type {
  AccountResponse,
  CategoryResponse,
  CreateTransactionRequest,
  PaginatedResponse,
  TransactionDirection,
  TransactionImportResponse,
  TransactionAttachmentResponse,
  TransactionResponse,
  TransactionSplitRequest,
  TransactionSplitResponse,
  TransferCreateRequest,
  UpdateTransactionRequest,
} from "../api/types";

const PAGE_LIMIT = 20;
const UNASSIGNED_CATEGORY = "__none__";

type TransactionFormState = {
  account_id: string;
  amount: number | "";
  direction: TransactionDirection;
  category_id: string;
  merchant: string;
  note: string;
  tags: string;
  occurred_at: string;
};

type SplitFormState = {
  id: string;
  category_id: string;
  amount: number | "";
  note: string;
};

type TransactionFilters = {
  account_id: string;
  category_id: string;
  occurred_from: string;
  occurred_to: string;
  search: string;
  tag: string;
};

const INITIAL_FILTERS: TransactionFilters = {
  account_id: "",
  category_id: "",
  occurred_from: "",
  occurred_to: "",
  search: "",
  tag: "",
};

export default function Transactions() {
  const [transactions, setTransactions] = useState<TransactionResponse[]>([]);
  const [accounts, setAccounts] = useState<AccountResponse[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [opened, setOpened] = useState(false);
  const [transferOpened, setTransferOpened] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<TransactionImportResponse | null>(null);
  const [editingTransaction, setEditingTransaction] = useState<TransactionResponse | null>(null);
  const [filters, setFilters] = useState<TransactionFilters>(INITIAL_FILTERS);
  const [filterInputs, setFilterInputs] = useState<TransactionFilters>(INITIAL_FILTERS);
  const [form, setForm] = useState<TransactionFormState>(emptyForm());
  const [useSplits, setUseSplits] = useState(false);
  const [splits, setSplits] = useState<SplitFormState[]>([]);
  const [attachmentFile, setAttachmentFile] = useState<File | null>(null);
  const [attachmentUploading, setAttachmentUploading] = useState(false);
  const [attachments, setAttachments] = useState<TransactionAttachmentResponse[]>([]);
  const [transferForm, setTransferForm] = useState<TransferFormState>(emptyTransferForm());
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkCategoryId, setBulkCategoryId] = useState<string>(UNASSIGNED_CATEGORY);
  const [bulkSubmitting, setBulkSubmitting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);

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

  const bulkCategoryOptions = useMemo(
    () => [
      { value: UNASSIGNED_CATEGORY, label: "Uncategorized" },
      ...categories.map((category) => ({
        value: category.id,
        label: category.icon ? `${category.icon} ${category.name}` : category.name,
      })),
    ],
    [categories],
  );

  useEffect(() => {
    void loadReferenceData();
  }, []);

  useEffect(() => {
    void loadTransactions(page, filters);
  }, [page, filters]);

  const splitTotal = useMemo(
    () =>
      splits.reduce((total, split) => {
        if (split.amount === "" || Number.isNaN(Number(split.amount))) {
          return total;
        }
        return total + Number(split.amount);
      }, 0),
    [splits],
  );

  const addSplitRow = () => {
    setSplits((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        category_id: "",
        amount: "",
        note: "",
      },
    ]);
  };

  const updateSplitRow = (
    id: string,
    field: keyof SplitFormState,
    value: string | number | "",
  ) => {
    setSplits((current) =>
      current.map((split) => (split.id === id ? { ...split, [field]: value } : split)),
    );
  };

  const removeSplitRow = (id: string) => {
    setSplits((current) => current.filter((split) => split.id !== id));
  };

  const onOpenCreate = () => {
    setEditingTransaction(null);
    setForm(emptyForm(accounts[0]?.id));
    setUseSplits(false);
    setSplits([]);
    setAttachmentFile(null);
    setAttachments([]);
    setOpened(true);
  };

  const onOpenTransfer = () => {
    setTransferForm(emptyTransferForm(accounts[0]?.id));
    setTransferOpened(true);
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
      tags: (transaction.tags ?? []).join(", "),
      occurred_at: toDateTimeLocal(transaction.occurred_at),
    });
    if (transaction.splits && transaction.splits.length > 0) {
      setUseSplits(true);
      setSplits(
        transaction.splits.map((split) => ({
          id: split.id,
          category_id: split.category_id ?? "",
          amount: toNumber(split.amount),
          note: split.note ?? "",
        })),
      );
    } else {
      setUseSplits(false);
      setSplits([]);
    }
    setAttachmentFile(null);
    setAttachments(transaction.attachments ?? []);
    setOpened(true);
  };

  const refreshEditingTransaction = async (transactionId: string) => {
    const updated = await apiFetch<TransactionResponse>(`/transactions/${transactionId}`);
    setEditingTransaction(updated);
    setAttachments(updated.attachments ?? []);
    await loadTransactions(page, filters);
  };

  const onSubmit = async () => {
    const shouldUseSplits = useSplits;
    if (
      !form.account_id ||
      (!shouldUseSplits && (form.amount === "" || form.amount <= 0)) ||
      !form.occurred_at
    ) {
      setError("Account, amount, and date/time are required");
      return;
    }
    if (shouldUseSplits && splits.length === 0) {
      setError("Add at least one split for this transaction");
      return;
    }
    if (shouldUseSplits && splitTotal <= 0) {
      setError("Split amounts must total more than zero");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const splitPayload: TransactionSplitRequest[] | undefined = shouldUseSplits
        ? splits.map((split) => ({
            category_id: split.category_id || null,
            amount: Number(split.amount || 0).toFixed(2),
            note: normalizeString(split.note),
          }))
        : undefined;
      if (editingTransaction) {
        const payload: UpdateTransactionRequest = {
          amount: shouldUseSplits ? splitTotal.toFixed(2) : Number(form.amount).toFixed(2),
          direction: form.direction,
          category_id: shouldUseSplits ? null : form.category_id || null,
          merchant: normalizeString(form.merchant),
          note: normalizeString(form.note),
          tags: parseTagsInput(form.tags),
          occurred_at: toIsoString(form.occurred_at),
          splits:
            splitPayload ??
            (editingTransaction.splits && editingTransaction.splits.length > 0 ? [] : undefined),
        };
        await apiFetch<TransactionResponse>(`/transactions/${editingTransaction.id}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        const payload: CreateTransactionRequest = {
          account_id: form.account_id,
          amount: shouldUseSplits ? splitTotal.toFixed(2) : Number(form.amount).toFixed(2),
          direction: form.direction,
          category_id: shouldUseSplits ? null : form.category_id || null,
          merchant: normalizeString(form.merchant) ?? undefined,
          note: normalizeString(form.note) ?? undefined,
          tags: parseTagsInput(form.tags) ?? undefined,
          occurred_at: toIsoString(form.occurred_at),
          splits: splitPayload ?? undefined,
        };
        await apiFetch<TransactionResponse>("/transactions", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }

      setOpened(false);
      setEditingTransaction(null);
      setForm(emptyForm(accounts[0]?.id));
      setUseSplits(false);
      setSplits([]);
      setAttachments([]);
      await loadTransactions(page, filters);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const onSubmitTransfer = async () => {
    if (
      !transferForm.from_account_id ||
      !transferForm.to_account_id ||
      transferForm.from_account_id === transferForm.to_account_id ||
      transferForm.amount === "" ||
      transferForm.amount <= 0 ||
      !transferForm.occurred_at
    ) {
      setError("Select two different accounts and provide a valid amount");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const payload: TransferCreateRequest = {
        from_account_id: transferForm.from_account_id,
        to_account_id: transferForm.to_account_id,
        amount: Number(transferForm.amount).toFixed(2),
        occurred_at: toIsoString(transferForm.occurred_at),
        note: normalizeString(transferForm.note),
      };
      await apiFetch("/transactions/transfer", { method: "POST", body: JSON.stringify(payload) });
      setTransferOpened(false);
      setTransferForm(emptyTransferForm(accounts[0]?.id));
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

  const onToggleSelect = (transactionId: string, checked: boolean) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (checked) {
        next.add(transactionId);
      } else {
        next.delete(transactionId);
      }
      return next;
    });
  };

  const onToggleSelectAll = (checked: boolean) => {
    if (!checked) {
      setSelectedIds(new Set());
      return;
    }
    setSelectedIds(new Set(transactions.map((transaction) => transaction.id)));
  };

  const onBulkUpdateCategory = async () => {
    if (!selectedIds.size) {
      return;
    }
    setBulkSubmitting(true);
    setError(null);
    try {
      await apiFetch("/transactions/bulk-category", {
        method: "POST",
        body: JSON.stringify({
          transaction_ids: Array.from(selectedIds),
          category_id: bulkCategoryId === UNASSIGNED_CATEGORY ? null : bulkCategoryId,
        }),
      });
      setSelectedIds(new Set());
      setBulkCategoryId(UNASSIGNED_CATEGORY);
      await loadTransactions(page, filters);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBulkSubmitting(false);
    }
  };

  const onImportCsv = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setImporting(true);
    setError(null);
    setImportResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const csrfToken = getCsrfToken();
      const response = await fetch(`${API_BASE_URL}/transactions/import`, {
        method: "POST",
        body: formData,
        credentials: "include",
        headers: csrfToken ? { "X-CSRF-Token": csrfToken } : undefined,
      });
      if (!response.ok) {
        const payload = await response.text();
        throw new ApiError(payload || "Import failed", response.status, payload);
      }
      const payload = (await response.json()) as TransactionImportResponse;
      setImportResult(payload);
      await loadTransactions(page, filters);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setImporting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const onUploadAttachment = async () => {
    if (!editingTransaction || !attachmentFile) {
      return;
    }
    setAttachmentUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", attachmentFile);
      const csrfToken = getCsrfToken();
      const response = await fetch(
        `${API_BASE_URL}/transactions/${editingTransaction.id}/attachments`,
        {
          method: "POST",
          body: formData,
          credentials: "include",
          headers: csrfToken ? { "X-CSRF-Token": csrfToken } : undefined,
        },
      );
      if (!response.ok) {
        const payload = await response.text();
        throw new ApiError(payload || "Upload failed", response.status, payload);
      }
      const payload = (await response.json()) as TransactionAttachmentResponse;
      setAttachmentFile(null);
      setAttachments((current) => [...current, payload]);
      await refreshEditingTransaction(editingTransaction.id);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setAttachmentUploading(false);
    }
  };

  const onDeleteAttachment = async (attachmentId: string) => {
    if (!editingTransaction) {
      return;
    }
    const confirmed = window.confirm("Delete this attachment?");
    if (!confirmed) {
      return;
    }
    setAttachmentUploading(true);
    setError(null);
    try {
      await apiFetch<void>(
        `/transactions/${editingTransaction.id}/attachments/${attachmentId}`,
        { method: "DELETE" },
      );
      setAttachments((current) =>
        current.filter((attachment) => attachment.id !== attachmentId),
      );
      await refreshEditingTransaction(editingTransaction.id);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setAttachmentUploading(false);
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
  const allSelected =
    transactions.length > 0 && transactions.every((transaction) => selectedIds.has(transaction.id));
  const someSelected = selectedIds.size > 0 && !allSelected;

  return (
    <Stack mt="md" gap="md">
      <Group justify="space-between">
        <Title order={2}>Transactions</Title>
        <Group>
          <Text c="dimmed" size="sm">
            {total} total
          </Text>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            style={{ display: "none" }}
            onChange={onImportCsv}
          />
          <Button
            variant="light"
            loading={importing}
            onClick={() => fileInputRef.current?.click()}
          >
            Import CSV
          </Button>
          <Button variant="light" onClick={onOpenTransfer} disabled={accounts.length < 2}>
            Transfer
          </Button>
          <Button variant="light" onClick={() => void onExportCsv()}>
            Export CSV
          </Button>
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

      {importResult ? (
        <Alert color="teal" title="Import completed">
          Imported {importResult.imported} rows, skipped {importResult.skipped}.
        </Alert>
      ) : null}

      {selectedIds.size ? (
        <Group justify="space-between" align="center">
          <Text size="sm" c="dimmed">
            {selectedIds.size} selected
          </Text>
          <Group>
            <Select
              label="Bulk category"
              data={bulkCategoryOptions}
              value={bulkCategoryId}
              onChange={(value) =>
                setBulkCategoryId(value ?? UNASSIGNED_CATEGORY)
              }
              w={240}
            />
            <Button loading={bulkSubmitting} onClick={onBulkUpdateCategory}>
              Apply
            </Button>
            <Button variant="subtle" onClick={() => setSelectedIds(new Set())}>
              Clear
            </Button>
          </Group>
        </Group>
      ) : null}

      <Group align="end" wrap="wrap">
        <TextInput
          label="Search"
          placeholder="Merchant or note"
          value={filterInputs.search}
          onChange={(event) =>
            setFilterInputs((current) => ({ ...current, search: event.currentTarget.value }))
          }
          w={240}
        />
        <TextInput
          label="Tag"
          placeholder="e.g. groceries"
          value={filterInputs.tag}
          onChange={(event) =>
            setFilterInputs((current) => ({ ...current, tag: event.currentTarget.value }))
          }
          w={200}
        />
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

      <ResponsiveTable minWidth={900}>
        <Table striped highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th w={40}>
                <Checkbox
                  checked={allSelected}
                  indeterminate={someSelected}
                  onChange={(event) => onToggleSelectAll(event.currentTarget.checked)}
                />
              </Table.Th>
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
              const splits = transaction.splits ?? [];
              const isTransfer = Boolean(transaction.transfer_id);
              const transferPartner = isTransfer
                ? transactions.find(
                    (candidate) =>
                      candidate.transfer_id === transaction.transfer_id &&
                      candidate.id !== transaction.id,
                  )
                : null;
              const transferAccountName = transferPartner
                ? accountLookup.get(transferPartner.account_id)?.name
                : null;
              const transferLabel = isTransfer
                ? transferAccountName
                  ? transaction.direction === "OUT"
                    ? `Transfer to ${transferAccountName}`
                    : `Transfer from ${transferAccountName}`
                  : "Transfer"
                : null;

              return (
                <Table.Tr key={transaction.id}>
                  <Table.Td>
                    <Checkbox
                      checked={selectedIds.has(transaction.id)}
                      onChange={(event) =>
                        onToggleSelect(transaction.id, event.currentTarget.checked)
                      }
                    />
                  </Table.Td>
                  <Table.Td>{formatDate(transaction.occurred_at)}</Table.Td>
                  <Table.Td>
                    <Stack gap={0}>
                      <Text>
                        {transferLabel ?? transaction.merchant ?? "No description"}
                      </Text>
                      {transaction.note ? (
                        <Text size="xs" c="dimmed">
                          {transaction.note}
                        </Text>
                      ) : null}
                      {transaction.tags && transaction.tags.length ? (
                        <Group gap={6} mt={4} wrap="wrap">
                          {transaction.tags.map((tag) => (
                            <Badge key={tag} size="xs" variant="light" color="gray">
                              {tag}
                            </Badge>
                          ))}
                        </Group>
                      ) : null}
                    </Stack>
                  </Table.Td>
                  <Table.Td>
                    {isTransfer ? (
                      <Badge color="blue" variant="light">
                        Transfer
                      </Badge>
                    ) : splits.length > 0 ? (
                      <Stack gap={4}>
                        <Badge color="gray" variant="light">
                          Split transaction
                        </Badge>
                        {splits.map((split) => {
                          const splitCategory = split.category_id
                            ? categoryLookup.get(split.category_id)
                            : null;
                          return (
                            <Group key={split.id} gap={6} wrap="wrap">
                              <Badge color={splitCategory?.color ?? "gray"} variant="light">
                                {splitCategory?.icon ? `${splitCategory.icon} ` : ""}
                                {splitCategory?.name ?? "Uncategorized"}
                              </Badge>
                              <Text size="xs" c="dimmed">
                                ${split.amount}
                              </Text>
                            </Group>
                          );
                        })}
                      </Stack>
                    ) : category ? (
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
                <Table.Td colSpan={7}>
                  <Text ta="center" c="dimmed">
                    No transactions found for current filters.
                  </Text>
                </Table.Td>
              </Table.Tr>
            ) : null}
          </Table.Tbody>
        </Table>
      </ResponsiveTable>

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
              value={useSplits ? splitTotal : form.amount}
              onChange={(value) => setForm((current) => ({ ...current, amount: value }))}
              min={0}
              decimalScale={2}
              fixedDecimalScale
              prefix="$"
              required
              disabled={useSplits}
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
          <Switch
            label="Split transaction"
            checked={useSplits}
            onChange={(event) => {
              const checked = event.currentTarget.checked;
              setUseSplits(checked);
              if (checked && splits.length === 0) {
                addSplitRow();
              }
              if (!checked) {
                setSplits([]);
              }
            }}
          />
          {useSplits ? (
            <Stack gap="xs">
              <Text size="sm" fw={600}>
                Splits
              </Text>
              {splits.map((split) => (
                <Group key={split.id} align="end" wrap="wrap">
                  <Select
                    label="Category"
                    data={filteredCategoryOptions}
                    value={split.category_id || null}
                    onChange={(value) =>
                      updateSplitRow(split.id, "category_id", value ?? "")
                    }
                    searchable
                    clearable
                    w={260}
                  />
                  <NumberInput
                    label="Amount"
                    value={split.amount}
                    onChange={(value) => updateSplitRow(split.id, "amount", value ?? "")}
                    min={0}
                    decimalScale={2}
                    fixedDecimalScale
                    prefix="$"
                    w={160}
                  />
                  <TextInput
                    label="Note"
                    value={split.note}
                    onChange={(event) =>
                      updateSplitRow(split.id, "note", event.currentTarget.value)
                    }
                    w={220}
                  />
                  <ActionIcon
                    variant="subtle"
                    color="red"
                    onClick={() => removeSplitRow(split.id)}
                  >
                    ×
                  </ActionIcon>
                </Group>
              ))}
              <Button variant="light" onClick={addSplitRow}>
                Add split
              </Button>
              <Divider my="xs" />
            </Stack>
          ) : (
            <Select
              label="Category (optional)"
              placeholder="Uncategorized"
              data={filteredCategoryOptions}
              value={form.category_id || null}
              onChange={(value) =>
                setForm((current) => ({ ...current, category_id: value ?? "" }))
              }
              clearable
              searchable
            />
          )}
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
            label="Tags"
            placeholder="comma, separated, tags"
            value={form.tags}
            onChange={(event) =>
              setForm((current) => ({ ...current, tags: event.currentTarget.value }))
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
          {editingTransaction ? (
            <Stack gap="xs">
              <Divider label="Attachments" />
              <Group align="end" wrap="wrap">
                <FileInput
                  label="Upload file"
                  placeholder="Select attachment"
                  value={attachmentFile}
                  onChange={setAttachmentFile}
                  accept="image/*,application/pdf"
                  clearable
                  w={300}
                />
                <Button
                  variant="light"
                  loading={attachmentUploading}
                  onClick={onUploadAttachment}
                  disabled={!attachmentFile}
                >
                  Upload
                </Button>
              </Group>
              {attachments.length ? (
                <Stack gap="xs">
                  {attachments.map((attachment) => (
                    <Group key={attachment.id} justify="space-between" wrap="wrap">
                      <Text size="sm">{attachment.filename}</Text>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          variant="subtle"
                          component="a"
                          href={`${API_BASE_URL}/transactions/${editingTransaction.id}/attachments/${attachment.id}`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Download
                        </Button>
                        <Button
                          size="xs"
                          variant="subtle"
                          color="red"
                          loading={attachmentUploading}
                          onClick={() => onDeleteAttachment(attachment.id)}
                        >
                          Delete
                        </Button>
                      </Group>
                    </Group>
                  ))}
                </Stack>
              ) : (
                <Text size="sm" c="dimmed">
                  No attachments yet.
                </Text>
              )}
            </Stack>
          ) : (
            <Text size="sm" c="dimmed">
              Attachments can be added after creating the transaction.
            </Text>
          )}
          <Button onClick={onSubmit} loading={submitting}>
            {editingTransaction ? "Update transaction" : "Create transaction"}
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={transferOpened}
        onClose={() => setTransferOpened(false)}
        title="Transfer between accounts"
        centered
      >
        <Stack>
          <Select
            label="From account"
            data={accountOptions}
            value={transferForm.from_account_id || null}
            onChange={(value) =>
              setTransferForm((current) => ({ ...current, from_account_id: value ?? "" }))
            }
            searchable
            required
          />
          <Select
            label="To account"
            data={accountOptions}
            value={transferForm.to_account_id || null}
            onChange={(value) =>
              setTransferForm((current) => ({ ...current, to_account_id: value ?? "" }))
            }
            searchable
            required
          />
          <NumberInput
            label="Amount"
            value={transferForm.amount}
            onChange={(value) =>
              setTransferForm((current) => ({
                ...current,
                amount: typeof value === "number" && !Number.isNaN(value) ? value : "",
              }))
            }
            min={0}
            decimalScale={2}
            fixedDecimalScale
            prefix="$"
            required
          />
          <TextInput
            label="Occurred at"
            type="datetime-local"
            value={transferForm.occurred_at}
            onChange={(event) =>
              setTransferForm((current) => ({ ...current, occurred_at: event.currentTarget.value }))
            }
            required
          />
          <TextInput
            label="Note"
            value={transferForm.note}
            onChange={(event) =>
              setTransferForm((current) => ({ ...current, note: event.currentTarget.value }))
            }
          />
          <Button onClick={onSubmitTransfer} loading={submitting}>
            Create transfer
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
      if (targetFilters.tag.trim()) {
        params.set("tag", targetFilters.tag.trim());
      }
      if (targetFilters.occurred_from) {
        params.set("occurred_from", `${targetFilters.occurred_from}T00:00:00Z`);
      }
      if (targetFilters.occurred_to) {
        params.set("occurred_to", `${targetFilters.occurred_to}T23:59:59Z`);
      }
      if (targetFilters.search.trim()) {
        params.set("search", targetFilters.search.trim());
      }

      const response = await apiFetch<PaginatedResponse<TransactionResponse>>(
        `/transactions?${params.toString()}`,
      );
      setTransactions(response.items);
      setTotal(response.total);
      setSelectedIds((current) => {
        if (!current.size) {
          return current;
        }
        const allowed = new Set(response.items.map((item) => item.id));
        return new Set(Array.from(current).filter((id) => allowed.has(id)));
      });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function onExportCsv() {
    const params = new URLSearchParams();
    if (filters.account_id) {
      params.set("account_id", filters.account_id);
    }
    if (filters.category_id) {
      params.set("category_id", filters.category_id);
    }
    if (filters.tag.trim()) {
      params.set("tag", filters.tag.trim());
    }
    if (filters.occurred_from) {
      params.set("occurred_from", `${filters.occurred_from}T00:00:00Z`);
    }
    if (filters.occurred_to) {
      params.set("occurred_to", `${filters.occurred_to}T23:59:59Z`);
    }
    if (filters.search.trim()) {
      params.set("search", filters.search.trim());
    }

    const response = await fetch(`${API_BASE_URL}/transactions/export?${params.toString()}`, {
      credentials: "include",
    });
    if (!response.ok) {
      setError(`Export failed (${response.status})`);
      return;
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "transactions.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
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
    tags: "",
    occurred_at: toDateTimeLocal(new Date().toISOString()),
  };
}

type TransferFormState = {
  from_account_id: string;
  to_account_id: string;
  amount: number | "";
  occurred_at: string;
  note: string;
};

function emptyTransferForm(defaultAccountId = ""): TransferFormState {
  return {
    from_account_id: defaultAccountId,
    to_account_id: "",
    amount: "",
    occurred_at: toDateTimeLocal(new Date().toISOString()),
    note: "",
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

function parseTagsInput(value: string): string[] | null {
  const normalized = value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
  return normalized.length ? normalized : null;
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
