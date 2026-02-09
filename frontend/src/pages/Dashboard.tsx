import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Grid,
  Group,
  Loader,
  Select,
  Stack,
  Text,
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
import { ApiError, apiFetch } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import type {
  BudgetProgressResponse,
  CashflowTrendResponse,
  CategoryBreakdownResponse,
  DashboardSummaryResponse,
  ReportGranularity,
  ReportPeriod,
} from "../api/types";

const PERIOD_OPTIONS: Array<{ value: ReportPeriod; label: string }> = [
  { value: "week", label: "This Week" },
  { value: "month", label: "This Month" },
  { value: "year", label: "This Year" },
];

const CHART_COLORS = ["#2E86AB", "#F18F01", "#C73E1D", "#5FAD56", "#7D5BA6", "#008B8B"];

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [period, setPeriod] = useState<ReportPeriod>("month");
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [cashflow, setCashflow] = useState<CashflowTrendResponse | null>(null);
  const [categories, setCategories] = useState<CategoryBreakdownResponse | null>(null);
  const [budgetProgress, setBudgetProgress] = useState<BudgetProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadDashboard(period);
  }, [period]);

  const onLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

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
            <Group justify="space-between">
              <Title order={4}>Budget Overview</Title>
              <Button variant="subtle" size="xs" onClick={() => navigate("/budgets")}>
                View all budgets
              </Button>
            </Group>
            {!budgetProgress || budgetProgress.items.length === 0 ? (
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
    </Stack>
  );

  async function loadDashboard(selectedPeriod: ReportPeriod) {
    setLoading(true);
    setError(null);
    try {
      const dashboard = await apiFetch<DashboardSummaryResponse>(
        `/reporting/dashboard?period=${selectedPeriod}`,
      );
      setSummary(dashboard);

      const granularity: ReportGranularity = selectedPeriod === "year" ? "month" : "day";
      const [cashflowData, categoryData, budgetProgressData] = await Promise.all([
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
        apiFetch<BudgetProgressResponse>(
          `/budgets/progress?month=${encodeURIComponent(dashboard.to_date.slice(0, 7))}`,
        ),
      ]);
      setCashflow(cashflowData);
      setCategories(categoryData);
      setBudgetProgress(budgetProgressData);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
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
