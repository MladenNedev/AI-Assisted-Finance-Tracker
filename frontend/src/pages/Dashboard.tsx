import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Grid,
  Group,
  Loader,
  Modal,
  NumberInput,
  Progress,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import {
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { API_BASE_URL, ApiError, apiFetch } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import type {
  BudgetProgressResponse,
  CashflowTrendResponse,
  CreateTransactionRequest,
  CategoryBreakdownResponse,
  CategoryTrendResponse,
  DashboardSummaryResponse,
  PaginatedResponse,
  ReportGranularity,
  ReportPeriod,
  AccountResponse,
  CategoryResponse,
} from "../api/types";

const PERIOD_OPTIONS: Array<{ value: ReportPeriod; label: string }> = [
  { value: "week", label: "This Week" },
  { value: "month", label: "This Month" },
  { value: "year", label: "This Year" },
  { value: "custom", label: "Custom Range" },
];

const CHART_COLORS = ["#2E86AB", "#F18F01", "#C73E1D", "#5FAD56", "#7D5BA6", "#008B8B"];

const EXPORT_OPTIONS = [
  { value: "dashboard", label: "Dashboard summary" },
  { value: "cashflow", label: "Cashflow trend" },
  { value: "categories", label: "Category breakdown" },
  { value: "category_trend", label: "Category trend" },
];

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [period, setPeriod] = useState<ReportPeriod>("month");
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [cashflow, setCashflow] = useState<CashflowTrendResponse | null>(null);
  const [categories, setCategories] = useState<CategoryBreakdownResponse | null>(null);
  const [categoryTrend, setCategoryTrend] = useState<CategoryTrendResponse | null>(null);
  const [budgetProgress, setBudgetProgress] = useState<BudgetProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exportType, setExportType] = useState<string>("cashflow");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [quickOpen, setQuickOpen] = useState(false);
  const [quickSubmitting, setQuickSubmitting] = useState(false);
  const [quickError, setQuickError] = useState<string | null>(null);
  const [quickAccounts, setQuickAccounts] = useState<AccountResponse[]>([]);
  const [quickCategories, setQuickCategories] = useState<CategoryResponse[]>([]);
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [quickForm, setQuickForm] = useState({
    account_id: "",
    amount: 0 as number | "",
    direction: "OUT" as "IN" | "OUT",
    category_id: "",
    merchant: "",
    note: "",
    occurred_at: toDateTimeLocal(new Date().toISOString()),
  });

  useEffect(() => {
    if (period === "custom") {
      if (customFrom && customTo) {
        void loadDashboard(period, customFrom, customTo);
      } else {
        setError("Select a start and end date for the custom range.");
        setLoading(false);
      }
      return;
    }
    void loadDashboard(period);
  }, [period, customFrom, customTo]);

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const exportGranularity = useMemo(
    () =>
      period === "year" ? "month" : period === "month" ? "week" : "day",
    [period],
  );

  const cashflowSeries = useMemo(() => {
    if (!cashflow) {
      return [];
    }
    return cashflow.points.map((point) => ({
      label: formatPeriodLabel(point.period, cashflow.granularity),
      income: toNumber(point.income),
      expenses: toNumber(point.expenses),
      net: toNumber(point.net),
    }));
  }, [cashflow]);

  const categorySeries = useMemo(() => {
    if (!categories) {
      return [];
    }
    return categories.categories.slice(0, 6).map((item) => ({
      id: item.category_id ?? item.category_name,
      label: item.category_name,
      amount: toNumber(item.amount),
      color: item.color,
      percentage: item.percentage,
    }));
  }, [categories]);

  const categoryTrendSeries = useMemo(() => {
    if (!categoryTrend) {
      return { data: [], keys: [] as Array<{ key: string; label: string; color: string }> };
    }
    const byPeriod = new Map<string, Record<string, number>>();
    const labels = new Map<string, { label: string; color: string }>();

    for (const point of categoryTrend.points) {
      const periodKey = point.period;
      const entry = byPeriod.get(periodKey) ?? { period: periodKey };
      const key = point.category_id ?? point.category_name;
      entry[key] = toNumber(point.amount);
      byPeriod.set(periodKey, entry);
      labels.set(key, {
        label: point.category_name,
        color: point.color ?? CHART_COLORS[labels.size % CHART_COLORS.length],
      });
    }

    const data = Array.from(byPeriod.values()).sort((a, b) => {
      const left = new Date(String(a.period)).getTime();
      const right = new Date(String(b.period)).getTime();
      return left - right;
    });
    const keys = Array.from(labels.entries()).map(([key, meta]) => ({
      key,
      label: meta.label,
      color: meta.color,
    }));
    return { data, keys };
  }, [categoryTrend]);

  const quickCategoryOptions = useMemo(
    () =>
      quickCategories
        .filter((category) => category.is_income === (quickForm.direction === "IN"))
        .map((category) => ({
          value: category.id,
          label: category.icon ? `${category.icon} ${category.name}` : category.name,
        })),
    [quickCategories, quickForm.direction],
  );

  const quickAccountOptions = useMemo(
    () =>
      quickAccounts.map((account) => ({
        value: account.id,
        label: `${account.name} (${account.currency} ${account.current_balance})`,
      })),
    [quickAccounts],
  );

  return (
    <Stack mt="md" gap="md">
      <Group justify="space-between" align="center">
        <Title order={2}>Reporting Dashboard</Title>
        <Group>
          <Select
            value={period}
            onChange={(value) => setPeriod((value as ReportPeriod) ?? "month")}
            data={PERIOD_OPTIONS}
            w={160}
          />
          {period === "custom" ? (
            <Group>
              <TextInput
                label="From"
                type="date"
                value={customFrom}
                onChange={(event) => setCustomFrom(event.currentTarget.value)}
              />
              <TextInput
                label="To"
                type="date"
                value={customTo}
                onChange={(event) => setCustomTo(event.currentTarget.value)}
              />
            </Group>
          ) : null}
          <Select
            value={exportType}
            onChange={(value) => setExportType(value ?? "cashflow")}
            data={EXPORT_OPTIONS}
            w={180}
          />
          <Button variant="light" onClick={onExportCsv} loading={exporting} disabled={!summary}>
            Export CSV
          </Button>
          <Button variant="outline" onClick={openQuickAdd}>
            Quick add
          </Button>
          <Button variant="light" onClick={onLogout}>
            Logout
          </Button>
        </Group>
      </Group>

      <Text c="dimmed" size="sm">
        Signed in as {user?.email}
      </Text>

      {error ? (
        <Alert color="red" title="Failed to load dashboard">
          {error}
        </Alert>
      ) : null}

      {exportError ? (
        <Alert color="red" title="Export failed">
          {exportError}
        </Alert>
      ) : null}

      {loading ? (
        <Group justify="center" py="xl">
          <Loader />
        </Group>
      ) : null}

      {!loading && summary ? (
        <>
          <Grid>
            <Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
              <SummaryCard label="Income" value={summary.income} color="teal" />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
              <SummaryCard label="Expenses" value={summary.expenses} color="red" />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
              <SummaryCard label="Net Cashflow" value={summary.net} />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
              <SummaryCard label="Total Balance" value={summary.total_balance} color="blue" />
            </Grid.Col>
          </Grid>

          <Grid>
            <Grid.Col span={{ base: 12, lg: 8 }}>
              <Card withBorder radius="md" p="lg">
                <Title order={4} mb="md">
                  Cashflow Trend
                </Title>
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={cashflowSeries}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="income" stroke="#2F9E44" strokeWidth={2} />
                    <Line type="monotone" dataKey="expenses" stroke="#E03131" strokeWidth={2} />
                    <Line type="monotone" dataKey="net" stroke="#1C7ED6" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
            </Grid.Col>

            <Grid.Col span={{ base: 12, lg: 4 }}>
              <Card withBorder radius="md" p="lg">
                <Title order={4} mb="md">
                  Expense Categories
                </Title>
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie
                      data={categorySeries}
                      dataKey="amount"
                      nameKey="label"
                      innerRadius={45}
                      outerRadius={80}
                      label
                    >
                      {categorySeries.map((item, index) => (
                        <Cell
                          key={item.id}
                          fill={item.color ?? CHART_COLORS[index % CHART_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <Stack gap={6} mt="sm">
                  {categorySeries.map((item, index) => (
                    <Group key={item.id} justify="space-between">
                      <Group gap={8}>
                        <div
                          style={{
                            width: 10,
                            height: 10,
                            borderRadius: 2,
                            backgroundColor:
                              item.color ?? CHART_COLORS[index % CHART_COLORS.length],
                          }}
                        />
                        <Text size="sm">{item.label}</Text>
                      </Group>
                      <Text size="sm" fw={600}>
                        ${item.amount.toFixed(2)}
                      </Text>
                    </Group>
                  ))}
                </Stack>
              </Card>
            </Grid.Col>
          </Grid>

          <Card withBorder radius="md" p="lg">
            <Title order={4} mb="md">
              Category Trend
            </Title>
            {categoryTrendSeries.data.length ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={categoryTrendSeries.data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="period"
                    tickFormatter={(value) =>
                      formatPeriodLabel(String(value), categoryTrend?.granularity ?? "day")
                    }
                  />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {categoryTrendSeries.keys.map((item) => (
                    <Line
                      key={item.key}
                      type="monotone"
                      dataKey={item.key}
                      name={item.label}
                      stroke={item.color}
                      strokeWidth={2}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <Text c="dimmed" size="sm">
                No category trend data yet.
              </Text>
            )}
          </Card>

          <Card withBorder radius="md" p="lg">
            <Group justify="space-between">
              <Title order={4}>Budget Overview (Current Month)</Title>
              <Button variant="subtle" size="xs" onClick={() => navigate("/budgets")}>
                View all budgets
              </Button>
            </Group>
            {budgetProgress === null ? (
              <Text c="dimmed" size="sm" mt="sm">
                Budget overview unavailable.
              </Text>
            ) : budgetProgress.items.length === 0 ? (
              <Text c="dimmed" size="sm" mt="sm">
                No budgets configured for this month.
              </Text>
            ) : (
              <Stack gap="sm" mt="sm">
                {budgetProgress.items.slice(0, 3).map((item) => (
                  <div key={item.budget_id}>
                    <Group justify="space-between" mb={6}>
                      <Text size="sm" fw={600}>
                        {item.category_name}
                      </Text>
                      <Text size="sm" c="dimmed">
                        ${item.spent_amount} / ${item.limit_amount}
                      </Text>
                    </Group>
                    <Progress
                      value={Math.min(item.percentage_used, 100)}
                      color={budgetStatusColor(item.status)}
                      size="md"
                    />
                  </div>
                ))}
              </Stack>
            )}
          </Card>

          <Card withBorder radius="md" p="lg">
            <Group justify="space-between">
              <Title order={4}>Account Balances</Title>
              <Text size="sm" c="dimmed">
                {summary.account_count} active accounts
              </Text>
            </Group>
            <Stack gap={8} mt="sm">
              {summary.accounts.map((account) => (
                <Group key={account.account_id} justify="space-between">
                  <Group gap={8}>
                    <Text fw={500}>{account.account_name}</Text>
                    <Text size="xs" c="dimmed">
                      {account.account_type}
                    </Text>
                  </Group>
                  <Text fw={600}>
                    {account.currency} {toNumber(account.balance).toFixed(2)}
                  </Text>
                </Group>
              ))}
            </Stack>
          </Card>
        </>
      ) : null}

      <Modal
        opened={quickOpen}
        onClose={() => setQuickOpen(false)}
        title="Quick add transaction"
        centered
        size="lg"
      >
        <Stack>
          {quickError ? (
            <Alert color="red" title="Unable to add transaction">
              {quickError}
            </Alert>
          ) : null}
          <Select
            label="Account"
            data={quickAccountOptions}
            value={quickForm.account_id || null}
            onChange={(value) =>
              setQuickForm((current) => ({ ...current, account_id: value ?? "" }))
            }
            searchable
            required
          />
          <Group grow>
            <NumberInput
              label="Amount"
              value={quickForm.amount}
              onChange={(value) => setQuickForm((current) => ({ ...current, amount: value }))}
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
              value={quickForm.direction}
              onChange={(value) =>
                setQuickForm((current) => ({
                  ...current,
                  direction: (value as "IN" | "OUT" | null) ?? "OUT",
                  category_id: "",
                }))
              }
            />
          </Group>
          <Select
            label="Category (optional)"
            placeholder="Uncategorized"
            data={quickCategoryOptions}
            value={quickForm.category_id || null}
            onChange={(value) =>
              setQuickForm((current) => ({ ...current, category_id: value ?? "" }))
            }
            clearable
            searchable
          />
          <TextInput
            label="Merchant / Description"
            value={quickForm.merchant}
            onChange={(event) =>
              setQuickForm((current) => ({ ...current, merchant: event.currentTarget.value }))
            }
          />
          <TextInput
            label="Note"
            value={quickForm.note}
            onChange={(event) =>
              setQuickForm((current) => ({ ...current, note: event.currentTarget.value }))
            }
          />
          <TextInput
            label="Occurred at"
            type="datetime-local"
            value={quickForm.occurred_at}
            onChange={(event) =>
              setQuickForm((current) => ({ ...current, occurred_at: event.currentTarget.value }))
            }
            required
          />
          <Button onClick={submitQuickAdd} loading={quickSubmitting}>
            Add transaction
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );

  async function loadDashboard(
    selectedPeriod: ReportPeriod,
    customFromDate?: string,
    customToDate?: string,
  ) {
    setLoading(true);
    setError(null);
    try {
      const dashboardParams = new URLSearchParams({
        period: selectedPeriod,
      });
      if (selectedPeriod === "custom" && customFromDate && customToDate) {
        dashboardParams.set("from_date", `${customFromDate}T00:00:00Z`);
        dashboardParams.set("to_date", `${customToDate}T23:59:59Z`);
      }
      const dashboard = await apiFetch<DashboardSummaryResponse>(
        `/reporting/dashboard?${dashboardParams.toString()}`,
      );
      setSummary(dashboard);

      const granularity: ReportGranularity =
        selectedPeriod === "year" ? "month" : selectedPeriod === "month" ? "week" : "day";
      const [cashflowData, categoryData] = await Promise.all([
        apiFetch<CashflowTrendResponse>(
          `/reporting/cashflow?from_date=${encodeURIComponent(
            dashboard.from_date,
          )}&to_date=${encodeURIComponent(dashboard.to_date)}&granularity=${granularity}`,
        ),
        apiFetch<CategoryBreakdownResponse>(
          `/reporting/categories?from_date=${encodeURIComponent(
            dashboard.from_date,
          )}&to_date=${encodeURIComponent(dashboard.to_date)}&breakdown_type=expense&limit=8`,
        ),
      ]);
      setCashflow(cashflowData);
      setCategories(categoryData);

      const trendData = await apiFetch<CategoryTrendResponse>(
        `/reporting/category-trend?from_date=${encodeURIComponent(
          dashboard.from_date,
        )}&to_date=${encodeURIComponent(dashboard.to_date)}&granularity=${granularity}&breakdown_type=expense&limit=5`,
      );
      setCategoryTrend(trendData);

      try {
        const budgetProgressData = await apiFetch<BudgetProgressResponse>(
          `/budgets/progress?month=${encodeURIComponent(currentMonth())}`,
        );
        setBudgetProgress(budgetProgressData);
      } catch {
        setBudgetProgress(null);
      }
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function onExportCsv() {
    if (!summary) {
      setExportError("Load dashboard data before exporting.");
      return;
    }

    setExporting(true);
    setExportError(null);

    try {
      const params = new URLSearchParams({
        report_type: exportType,
        period,
      });
      if (exportType !== "dashboard") {
        params.set("from_date", summary.from_date);
        params.set("to_date", summary.to_date);
        params.set("granularity", exportGranularity);
      } else if (period === "custom") {
        params.set("from_date", summary.from_date);
        params.set("to_date", summary.to_date);
      }
      if (exportType === "categories") {
        params.set("breakdown_type", "expense");
        params.set("limit", "8");
      }
      if (exportType === "category_trend") {
        params.set("breakdown_type", "expense");
        params.set("granularity", exportGranularity);
        params.set("limit", "5");
      }

      const response = await fetch(`${API_BASE_URL}/reporting/export?${params.toString()}`, {
        credentials: "include",
      });
      if (!response.ok) {
        setExportError(`Export failed (${response.status})`);
        return;
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${exportType}_${summary.from_date.slice(0, 10)}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (requestError) {
      setExportError(getErrorMessage(requestError));
    } finally {
      setExporting(false);
    }
  }

  async function openQuickAdd() {
    setQuickError(null);
    setQuickOpen(true);
    if (!quickAccounts.length || !quickCategories.length) {
      try {
        const [accountResponse, categoryResponse] = await Promise.all([
          apiFetch<PaginatedResponse<AccountResponse>>("/accounts?limit=500&offset=0"),
          apiFetch<PaginatedResponse<CategoryResponse>>("/categories?limit=500&offset=0"),
        ]);
        setQuickAccounts(accountResponse.items);
        setQuickCategories(categoryResponse.items);
        setQuickForm((current) => ({
          ...current,
          account_id: accountResponse.items[0]?.id ?? "",
        }));
      } catch (requestError) {
        setQuickError(getErrorMessage(requestError));
      }
    }
  }

  async function submitQuickAdd() {
    if (!quickForm.account_id || quickForm.amount === "" || quickForm.amount <= 0) {
      setQuickError("Account and amount are required");
      return;
    }

    setQuickSubmitting(true);
    setQuickError(null);
    try {
      const payload: CreateTransactionRequest = {
        account_id: quickForm.account_id,
        amount: Number(quickForm.amount).toFixed(2),
        direction: quickForm.direction,
        category_id: quickForm.category_id || null,
        merchant: normalizeString(quickForm.merchant) ?? undefined,
        note: normalizeString(quickForm.note) ?? undefined,
        occurred_at: toIsoString(quickForm.occurred_at),
      };
      await apiFetch("/transactions", { method: "POST", body: JSON.stringify(payload) });
      setQuickOpen(false);
      await loadDashboard(period);
    } catch (requestError) {
      setQuickError(getErrorMessage(requestError));
    } finally {
      setQuickSubmitting(false);
    }
  }
}

function SummaryCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <Card withBorder radius="md" p="lg">
      <Text size="sm" c="dimmed">
        {label}
      </Text>
      <Text fw={700} size="xl" c={color}>
        ${toNumber(value).toFixed(2)}
      </Text>
    </Card>
  );
}

function toNumber(value: string): number {
  const parsed = Number.parseFloat(value);
  if (Number.isNaN(parsed)) {
    return 0;
  }
  return parsed;
}

function normalizeString(value: string): string | null {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }
  return normalized;
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

function currentMonth(): string {
  const now = new Date();
  return `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}`;
}

function formatPeriodLabel(value: string, granularity: ReportGranularity): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  if (granularity === "month") {
    return new Intl.DateTimeFormat("en-US", { month: "short", year: "2-digit" }).format(date);
  }
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date);
}

function budgetStatusColor(status: "on_track" | "warning" | "exceeded"): string {
  if (status === "exceeded") {
    return "red";
  }
  if (status === "warning") {
    return "yellow";
  }
  return "green";
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
