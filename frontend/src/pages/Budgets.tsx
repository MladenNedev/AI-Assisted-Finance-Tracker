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
  Switch,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ApiError, apiFetch } from "../api/client";
import type {
  BudgetSummaryItem,
  BudgetSummaryResponse,
  BudgetProgressItem,
  BudgetProgressResponse,
  CategoryResponse,
  CreateCategoryRequest,
  CopyBudgetsResponse,
  CreateBudgetRequest,
  PaginatedResponse,
  UpdateBudgetRequest,
} from "../api/types";

type BudgetTemplateItem = {
  name: string;
  percent: number;
  color?: string;
  icon?: string;
};

type BudgetTemplate = {
  key: string;
  label: string;
  description: string;
  items: BudgetTemplateItem[];
};

const BUDGET_TEMPLATES: BudgetTemplate[] = [
  {
    key: "50-30-20",
    label: "50/30/20",
    description: "Needs 50%, wants 30%, savings 20%",
    items: [
      { name: "Needs", percent: 50, color: "#2E86AB", icon: "🏠" },
      { name: "Wants", percent: 30, color: "#F18F01", icon: "🎯" },
      { name: "Savings", percent: 20, color: "#5FAD56", icon: "💰" },
    ],
  },
  {
    key: "zero-based",
    label: "Zero-based starter",
    description: "Common starter categories for zero-based budgeting",
    items: [
      { name: "Housing", percent: 30, color: "#2E86AB", icon: "🏠" },
      { name: "Food", percent: 15, color: "#F18F01", icon: "🍽️" },
      { name: "Transportation", percent: 10, color: "#C73E1D", icon: "🚗" },
      { name: "Utilities", percent: 10, color: "#7D5BA6", icon: "💡" },
      { name: "Health", percent: 5, color: "#008B8B", icon: "🩺" },
      { name: "Debt", percent: 10, color: "#E03131", icon: "📉" },
      { name: "Personal", percent: 5, color: "#5FAD56", icon: "🧘" },
      { name: "Entertainment", percent: 5, color: "#F18F01", icon: "🎟️" },
      { name: "Other", percent: 10, color: "#6C757D", icon: "📌" },
    ],
  },
];

export default function Budgets() {
  const [month, setMonth] = useState(currentMonth());
  const [items, setItems] = useState<BudgetProgressItem[]>([]);
  const [summaryItems, setSummaryItems] = useState<BudgetSummaryItem[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [opened, setOpened] = useState(false);
  const [editOpened, setEditOpened] = useState(false);
  const [templateOpened, setTemplateOpened] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [formCategoryId, setFormCategoryId] = useState<string | null>(null);
  const [formLimit, setFormLimit] = useState<number | "">("");
  const [formRollover, setFormRollover] = useState(false);
  const [editingBudget, setEditingBudget] = useState<BudgetProgressItem | null>(null);
  const [editLimit, setEditLimit] = useState<number | "">("");
  const [editRollover, setEditRollover] = useState(false);
  const [templateKey, setTemplateKey] = useState<string>(BUDGET_TEMPLATES[0]?.key ?? "");
  const [templateTotal, setTemplateTotal] = useState<number | "">("");
  const [templateCreateMissing, setTemplateCreateMissing] = useState(true);

  const categoryOptions = useMemo(
    () =>
      categories
        .filter((category) => !category.is_income)
        .map((category) => ({ value: category.id, label: category.name })),
    [categories],
  );

  const summarySeries = useMemo(
    () =>
      summaryItems.map((item) => ({
        month: formatMonthLabel(item.month),
        budgeted: toNumber(item.budgeted),
        spent: toNumber(item.spent),
      })),
    [summaryItems],
  );

  const alertSummary = useMemo(() => {
    if (!items.length) {
      return null;
    }
    const exceeded = items.filter((item) => item.status === "exceeded");
    const warning = items.filter((item) => item.status === "warning");
    const projected = items.filter((item) => toNumber(item.projected_diff) > 0);
    if (!exceeded.length && !warning.length && !projected.length) {
      return null;
    }
    return { exceeded, warning, projected };
  }, [items]);

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
        rollover_enabled: formRollover,
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

  const onApplyTemplate = async () => {
    const template = BUDGET_TEMPLATES.find((entry) => entry.key === templateKey);
    if (!template) {
      setError("Select a budget template to continue");
      return;
    }
    if (templateTotal === "" || templateTotal <= 0) {
      setError("Enter a total monthly budget to apply");
      return;
    }

    setSubmitting(true);
    setError(null);
    setNotice(null);

    const normalizedTotal = Number(templateTotal);
    const budgetedCategories = new Set(items.map((item) => item.category_id));
    const categoryLookup = new Map(
      categories.map((category) => [normalizeName(category.name), category]),
    );

    let createdBudgets = 0;
    let skippedBudgets = 0;
    let createdCategories = 0;

    try {
      for (const entry of template.items) {
        const normalizedName = normalizeName(entry.name);
        let category = categoryLookup.get(normalizedName);

        if (!category) {
          if (!templateCreateMissing) {
            skippedBudgets += 1;
            continue;
          }
          const payload: CreateCategoryRequest = {
            name: entry.name,
            is_income: false,
            color: entry.color ?? null,
            icon: entry.icon ?? null,
          };
          category = await apiFetch<CategoryResponse>("/categories", {
            method: "POST",
            body: JSON.stringify(payload),
          });
          categoryLookup.set(normalizedName, category);
          createdCategories += 1;
        }

        if (budgetedCategories.has(category.id)) {
          skippedBudgets += 1;
          continue;
        }

        const limitAmount = (normalizedTotal * entry.percent) / 100;
        const payload: CreateBudgetRequest = {
          category_id: category.id,
          month,
          limit_amount: limitAmount.toFixed(2),
          rollover_enabled: false,
        };
        await apiFetch("/budgets", { method: "POST", body: JSON.stringify(payload) });
        createdBudgets += 1;
      }

      await loadMonth(month);
      setTemplateOpened(false);
      setTemplateTotal("");
      setNotice(
        `Template applied: ${createdBudgets} budgets created` +
          (createdCategories ? `, ${createdCategories} categories created.` : ".") +
          (skippedBudgets ? ` ${skippedBudgets} skipped.` : ""),
      );
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const onOpenEdit = (item: BudgetProgressItem) => {
    setEditingBudget(item);
    setEditLimit(Number(item.limit_amount));
    setEditRollover(item.rollover_enabled);
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
        rollover_enabled: editRollover,
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
          <Button variant="light" onClick={() => setTemplateOpened(true)}>
            Apply template
          </Button>
          <Button onClick={() => setOpened(true)}>Add budget</Button>
        </Group>
      </Group>

      {notice ? (
        <Alert color="teal" title="Budget update">
          {notice}
        </Alert>
      ) : null}

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

      {summaryItems.length ? (
        <Card withBorder radius="md" p="lg">
          <Group justify="space-between" mb="sm">
            <Title order={4}>Budget vs Actual</Title>
            <Text size="sm" c="dimmed">
              Last {summaryItems.length} months
            </Text>
          </Group>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={summarySeries}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="budgeted" fill="#2E86AB" name="Budgeted" />
              <Bar dataKey="spent" fill="#C73E1D" name="Spent" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      ) : null}

      {alertSummary ? (
        <Alert
          color={alertSummary.exceeded.length ? "red" : alertSummary.warning.length ? "yellow" : "blue"}
          title="Budget alerts"
        >
          {alertSummary.exceeded.length ? (
            <Text size="sm">
              Exceeded: {alertSummary.exceeded.map((item) => item.category_name).join(", ")}
            </Text>
          ) : null}
          {alertSummary.warning.length ? (
            <Text size="sm">
              Near limit: {alertSummary.warning.map((item) => item.category_name).join(", ")}
            </Text>
          ) : null}
          {alertSummary.projected.length ? (
            <Text size="sm">
              Projected over budget:{" "}
              {alertSummary.projected.map((item) => item.category_name).join(", ")}
            </Text>
          ) : (
            <Text size="sm">No projected overages yet.</Text>
          )}
        </Alert>
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
              {item.rollover_enabled ? (
                <Group justify="space-between">
                  <Text size="sm" c="dimmed">
                    Rollover: ${item.rollover_amount}
                  </Text>
                  <Text size="sm" c="dimmed">
                    Effective limit: ${item.effective_limit}
                  </Text>
                </Group>
              ) : null}
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
          <Switch
            label="Enable rollover"
            description="Carry unused budget into next month."
            checked={formRollover}
            onChange={(event) => setFormRollover(event.currentTarget.checked)}
          />
          <Button loading={submitting} onClick={onCreateBudget}>
            Save budget
          </Button>
        </Stack>
      </Modal>

      <Modal
        opened={templateOpened}
        onClose={() => setTemplateOpened(false)}
        title="Apply a budget template"
        centered
      >
        <Stack>
          <Select
            label="Template"
            data={BUDGET_TEMPLATES.map((template) => ({
              value: template.key,
              label: `${template.label} · ${template.description}`,
            }))}
            value={templateKey}
            onChange={(value) => setTemplateKey(value ?? "")}
          />
          <NumberInput
            label="Total monthly budget"
            value={templateTotal}
            onChange={setTemplateTotal}
            min={0}
            decimalScale={2}
            fixedDecimalScale
            prefix="$"
          />
          <Switch
            label="Create missing categories"
            description="Missing categories will be created automatically."
            checked={templateCreateMissing}
            onChange={(event) => setTemplateCreateMissing(event.currentTarget.checked)}
          />
          <Button loading={submitting} onClick={onApplyTemplate}>
            Apply template
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
          <Switch
            label="Enable rollover"
            description="Carry unused budget into next month."
            checked={editRollover}
            onChange={(event) => setEditRollover(event.currentTarget.checked)}
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
      const [progressResponse, categoriesResponse, summaryResponse] = await Promise.all([
        apiFetch<BudgetProgressResponse>(`/budgets/progress?month=${targetMonth}`),
        apiFetch<PaginatedResponse<CategoryResponse>>("/categories?limit=500&offset=0"),
        apiFetch<BudgetSummaryResponse>("/budgets/summary?months=6"),
      ]);
      setItems(progressResponse.items);
      setCategories(categoriesResponse.items);
      setSummaryItems(summaryResponse.items);
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
    setFormRollover(false);
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

function formatMonthLabel(value: string): string {
  const parsed = new Date(`${value}-01T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    year: "2-digit",
  }).format(parsed);
}

function toNumber(value: string): number {
  const parsed = Number.parseFloat(value);
  if (Number.isNaN(parsed)) {
    return 0;
  }
  return parsed;
}

function normalizeName(value: string): string {
  return value.trim().toLowerCase();
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
