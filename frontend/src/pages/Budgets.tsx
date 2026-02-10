import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  NumberInput,
  Progress,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { ApiError, apiFetch } from "../api/client";
import type {
  BudgetProgressItem,
  BudgetProgressResponse,
  CategoryResponse,
  CopyBudgetsResponse,
  CreateBudgetRequest,
  PaginatedResponse,
  UpdateBudgetRequest,
} from "../api/types";

export default function Budgets() {
  const [month, setMonth] = useState(currentMonth());
  const [items, setItems] = useState<BudgetProgressItem[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [opened, setOpened] = useState(false);
  const [editOpened, setEditOpened] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formCategoryId, setFormCategoryId] = useState<string | null>(null);
  const [formLimit, setFormLimit] = useState<number | "">("");
  const [editingBudget, setEditingBudget] = useState<BudgetProgressItem | null>(null);
  const [editLimit, setEditLimit] = useState<number | "">("");

  const categoryOptions = useMemo(
    () =>
      categories
        .filter((category) => !category.is_income)
        .map((category) => ({ value: category.id, label: category.name })),
    [categories],
  );

  useEffect(() => {
    void loadMonth(month);
  }, [month]);

  const onCreateBudget = async () => {
    if (!formCategoryId || formLimit === "" || formLimit <= 0) {
      setError("Please select a category and provide a valid monthly limit");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const payload: CreateBudgetRequest = {
        category_id: formCategoryId,
        month,
        limit_amount: Number(formLimit).toFixed(2),
      };
      await apiFetch("/budgets", { method: "POST", body: JSON.stringify(payload) });
      closeModal();
      await loadMonth(month);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const onCopyPreviousMonth = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const response = await apiFetch<CopyBudgetsResponse>("/budgets/copy-previous", {
        method: "POST",
        body: JSON.stringify({ target_month: month }),
      });
      if (response.created_count === 0) {
        setError("No budgets were copied (target month already populated or source month empty)");
      }
      await loadMonth(month);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const onOpenEdit = (item: BudgetProgressItem) => {
    setEditingBudget(item);
    setEditLimit(Number(item.limit_amount));
    setEditOpened(true);
  };

  const onSubmitEdit = async () => {
    if (!editingBudget || editLimit === "" || editLimit <= 0) {
      setError("Please provide a valid budget limit");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const payload: UpdateBudgetRequest = {
        limit_amount: Number(editLimit).toFixed(2),
      };
      await apiFetch(`/budgets/${editingBudget.budget_id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setEditOpened(false);
      setEditingBudget(null);
      setEditLimit("");
      await loadMonth(month);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const onDeleteBudget = async (item: BudgetProgressItem) => {
    const confirmed = window.confirm(`Delete budget for "${item.category_name}"?`);
    if (!confirmed) {
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await apiFetch<void>(`/budgets/${item.budget_id}`, { method: "DELETE" });
      await loadMonth(month);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Stack mt="md" gap="md">
      <Group justify="space-between" align="end">
        <div>
          <Title order={2}>Budgets</Title>
          <Text c="dimmed" size="sm">
            Expense budgets by category
          </Text>
        </div>
        <Group align="end">
          <TextInput
            label="Month"
            type="month"
            value={month}
            onChange={(event) => setMonth(event.currentTarget.value)}
          />
          <Button variant="light" loading={submitting} onClick={onCopyPreviousMonth}>
            Copy previous month
          </Button>
          <Button onClick={() => setOpened(true)}>Add budget</Button>
        </Group>
      </Group>

      {error ? (
        <Alert color="red" title="Budget request failed">
          {error}
        </Alert>
      ) : null}

      {loading ? (
        <Card withBorder radius="md" p="lg">
          <Text c="dimmed">Loading budgets...</Text>
        </Card>
      ) : null}

      {!loading && items.length === 0 ? (
        <Card withBorder radius="md" p="lg">
          <Text c="dimmed">No budgets configured for {month}.</Text>
        </Card>
      ) : null}

      {!loading
        ? items.map((item) => (
            <Card key={item.budget_id} withBorder radius="md" p="lg">
              <Group justify="space-between" align="center">
                <Group gap="xs">
                  <Text fw={600}>{item.category_name}</Text>
                  <Badge color={statusColor(item.status)}>{item.status.replace("_", " ")}</Badge>
                </Group>
                <Group gap="xs">
                  <Text fw={600}>
                    ${item.spent_amount} / ${item.limit_amount}
                  </Text>
                  <Button size="xs" variant="subtle" onClick={() => onOpenEdit(item)}>
                    Edit
                  </Button>
                  <Button
                    size="xs"
                    variant="subtle"
                    color="red"
                    loading={submitting}
                    onClick={() => onDeleteBudget(item)}
                  >
                    Delete
                  </Button>
                </Group>
              </Group>

              <Progress
                value={Math.min(item.percentage_used, 100)}
                color={statusColor(item.status)}
                size="lg"
                mt="sm"
                mb="sm"
              />

              <Group justify="space-between">
                <Text size="sm" c="dimmed">
                  Remaining: ${item.remaining_amount}
                </Text>
                <Text size="sm" c="dimmed">
                  Used: {item.percentage_used.toFixed(1)}%
                </Text>
              </Group>
              <Group justify="space-between">
                <Text size="sm" c="dimmed">
                  Daily avg: ${item.daily_average}
                </Text>
                <Text size="sm" c="dimmed">
                  Projected: ${item.projected_spend}
                </Text>
              </Group>
            </Card>
          ))
        : null}

      <Modal opened={opened} onClose={closeModal} title="Create budget" centered>
        <Stack>
          <Select
            label="Category"
            placeholder="Select expense category"
            value={formCategoryId}
            data={categoryOptions}
            onChange={(value) => setFormCategoryId(value)}
            searchable
          />
          <NumberInput
            label="Monthly limit"
            value={formLimit}
            onChange={setFormLimit}
            min={0}
            decimalScale={2}
            fixedDecimalScale
            prefix="$"
          />
          <Button loading={submitting} onClick={onCreateBudget}>
            Save budget
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={editOpened}
        onClose={() => setEditOpened(false)}
        title={editingBudget ? `Edit ${editingBudget.category_name} budget` : "Edit budget"}
        centered
      >
        <Stack>
          <NumberInput
            label="Monthly limit"
            value={editLimit}
            onChange={setEditLimit}
            min={0}
            decimalScale={2}
            fixedDecimalScale
            prefix="$"
          />
          <Button loading={submitting} onClick={onSubmitEdit}>
            Update budget
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );

  async function loadMonth(targetMonth: string) {
    setLoading(true);
    setError(null);
    try {
      const [progressResponse, categoriesResponse] = await Promise.all([
        apiFetch<BudgetProgressResponse>(`/budgets/progress?month=${targetMonth}`),
        apiFetch<PaginatedResponse<CategoryResponse>>("/categories?limit=500&offset=0"),
      ]);
      setItems(progressResponse.items);
      setCategories(categoriesResponse.items);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  function closeModal() {
    setOpened(false);
    setFormCategoryId(null);
    setFormLimit("");
  }
}

function statusColor(status: BudgetProgressItem["status"]): string {
  if (status === "exceeded") {
    return "red";
  }
  if (status === "warning") {
    return "yellow";
  }
  return "green";
}

function currentMonth(): string {
  const now = new Date();
  return `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}`;
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
