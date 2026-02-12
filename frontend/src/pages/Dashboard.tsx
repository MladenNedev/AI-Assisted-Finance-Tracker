import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Container,
  Grid,
  Group,
  Loader,
  Modal,
  NumberInput,
  Progress,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useHotkeys, useLocalStorage } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
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
  NetWorthTrendResponse,
  HeatmapResponse,
  MerchantSummaryResponse,
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
  const [netWorth, setNetWorth] = useState<NetWorthTrendResponse | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null);
  const [merchantSummary, setMerchantSummary] = useState<MerchantSummaryResponse | null>(null);
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
  const [customizeOpen, setCustomizeOpen] = useState(false);
  const [sectionVisibility, setSectionVisibility] = useLocalStorage<Record<string, boolean>>({
    key: "dashboard-sections",
    defaultValue: {
      cashflow: true,
      categories: true,
      categoryTrend: true,
      netWorth: true,
      heatmap: true,
      merchants: true,
      budgets: true,
      accounts: true,
    },
  });
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

  useHotkeys([
    ["mod+shift+a", () => openQuickAdd()],
    ["mod+shift+c", () => setCustomizeOpen(true)],
    ["mod+shift+e", () => summary && onExportCsv()],
  ]);

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
    const byPeriod = new Map<string, Record<string, number | string>>();
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
      const left = new Date(String(a.period ?? "")).getTime();
      const right = new Date(String(b.period ?? "")).getTime();
      return left - right;
    });
    const keys = Array.from(labels.entries()).map(([key, meta]) => ({
      key,
      label: meta.label,
      color: meta.color,
    }));
    return { data, keys };
  }, [categoryTrend]);

  const netWorthSeries = useMemo(() => {
    if (!netWorth) {
      return [];
    }
    return netWorth.points.map((point) => ({
      label: formatPeriodLabel(point.period, netWorth.granularity),
      balance: toNumber(point.balance),
    }));
  }, [netWorth]);

  const heatmapGrid = useMemo(() => buildHeatmapGrid(heatmap), [heatmap]);

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
    <Container size={1200} w="100%">
      <Stack mt="md" gap="md">
        <Group justify="space-between" align="center">
          <Title order={2}>Reporting Dashboard</Title>
          <Group gap="xs">
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
            <Button
              variant="light"
              size="sm"
              radius="md"
              onClick={onExportCsv}
              loading={exporting}
              disabled={!summary}
            >
              Export CSV
            </Button>
            <Button variant="light" size="sm" radius="md" onClick={() => setCustomizeOpen(true)}>
              Customize
            </Button>
            <Button variant="light" size="sm" radius="md" onClick={openQuickAdd}>
              Quick add
            </Button>
            <Button variant="light" size="sm" radius="md" color="red" onClick={onLogout}>
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

            <Grid align="stretch">
              {sectionVisibility.cashflow ? (
                <Grid.Col
                  span={{ base: 12, lg: sectionVisibility.categories ? 8 : 12 }}
                  style={{ display: "flex" }}
                >
                  <Card
                    withBorder
                    radius="md"
                    p="lg"
                    style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 300 }}
                  >
                    <Title order={4} mb="md">
                      Cashflow Trend
                    </Title>
                    <div style={{ flex: 1, minHeight: 320 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={cashflowSeries}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="label" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Line type="monotone" dataKey="income" stroke="#2F9E44" strokeWidth={2} />
                          <Line
                            type="monotone"
                            dataKey="expenses"
                            stroke="#E03131"
                            strokeWidth={2}
                          />
                          <Line type="monotone" dataKey="net" stroke="#1C7ED6" strokeWidth={2} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </Card>
                </Grid.Col>
              ) : null}

              {sectionVisibility.categories ? (
                <Grid.Col
                  span={{ base: 12, lg: sectionVisibility.cashflow ? 4 : 12 }}
                  style={{ display: "flex" }}
                >
                  <Card
                    withBorder
                    radius="md"
                    p="lg"
                    style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 300 }}
                  >
                    <Title order={4} mb="md">
                      Expense Categories
                    </Title>
                    <div style={{ flex: 1, minHeight: 240 }}>
                      <ResponsiveContainer width="100%" height="100%">
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
                    </div>
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
              ) : null}
            </Grid>

          {sectionVisibility.categoryTrend ? (
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
          ) : null}

          {sectionVisibility.netWorth ? (
            <Card withBorder radius="md" p="lg">
              <Title order={4} mb="md">
                Net Worth Trend
              </Title>
              {netWorthSeries.length ? (
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={netWorthSeries}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="balance" stroke="#1C7ED6" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Text c="dimmed" size="sm">
                  No net worth data yet.
                </Text>
              )}
            </Card>
          ) : null}

          {sectionVisibility.heatmap || sectionVisibility.merchants ? (
            <Grid align="stretch">
              {sectionVisibility.heatmap ? (
                <Grid.Col
                  span={{ base: 12, lg: sectionVisibility.merchants ? 7 : 12 }}
                  style={{ display: "flex" }}
                >
                  <Card
                    withBorder
                    radius="md"
                    p="lg"
                    style={{ flex: 1, display: "flex", flexDirection: "column" }}
                  >
                    <Group justify="space-between">
                      <Title order={4}>Spending Heatmap</Title>
                      <Text size="xs" c="dimmed">
                        Daily expenses
                      </Text>
                    </Group>
                    {heatmapGrid.weeks.length ? (
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(7, minmax(0, 1fr))",
                          gridAutoRows: "1fr",
                          gap: 6,
                          marginTop: 12,
                          minHeight: 220,
                          height: 220,
                          alignContent: "start",
                        }}
                      >
                        {heatmapGrid.weeks.flat().map((day) => (
                          <div
                            key={day.key}
                            title={`${day.label}: $${day.amount.toFixed(2)}`}
                            style={{
                              height: "100%",
                              borderRadius: 4,
                              backgroundColor: heatmapColor(day.amount, heatmapGrid.max),
                              border: "1px solid rgba(0,0,0,0.05)",
                            }}
                          />
                        ))}
                      </div>
                    ) : (
                      <Text c="dimmed" size="sm" mt="sm">
                        No heatmap data yet.
                      </Text>
                    )}
                  </Card>
                </Grid.Col>
              ) : null}
              {sectionVisibility.merchants ? (
                <Grid.Col
                  span={{ base: 12, lg: sectionVisibility.heatmap ? 5 : 12 }}
                  style={{ display: "flex" }}
                >
                  <Card
                    withBorder
                    radius="md"
                    p="lg"
                    style={{ flex: 1, display: "flex", flexDirection: "column" }}
                  >
                    <Group justify="space-between">
                      <Title order={4}>Top Merchants</Title>
                      <Text size="xs" c="dimmed">
                        Expenses
                      </Text>
                    </Group>
                    {merchantSummary && merchantSummary.merchants.length ? (
                      <Table mt="sm" highlightOnHover>
                        <thead>
                          <tr>
                            <th>Merchant</th>
                            <th style={{ textAlign: "right" }}>Total</th>
                            <th style={{ textAlign: "right" }}>Count</th>
                          </tr>
                        </thead>
                        <tbody>
                          {merchantSummary.merchants.map((merchant) => (
                            <tr key={merchant.merchant}>
                              <td>{merchant.merchant}</td>
                              <td style={{ textAlign: "right" }}>
                                ${toNumber(merchant.total).toFixed(2)}
                              </td>
                              <td style={{ textAlign: "right" }}>{merchant.count}</td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    ) : (
                      <Text c="dimmed" size="sm" mt="sm">
                        No merchant data yet.
                      </Text>
                    )}
                  </Card>
                </Grid.Col>
              ) : null}
            </Grid>
          ) : null}

          {sectionVisibility.budgets ? (
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
          ) : null}

          {sectionVisibility.accounts ? (
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
          ) : null}
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
              onChange={(value) => {
                const normalized =
                  typeof value === "number"
                    ? value
                    : value === "" || value === null
                      ? ""
                      : Number(value);
                setQuickForm((current) => ({ ...current, amount: normalized }));
              }}
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

      <Modal
        opened={customizeOpen}
        onClose={() => setCustomizeOpen(false)}
        title="Customize dashboard"
        centered
      >
        <Stack gap="sm">
          {[
            { key: "cashflow", label: "Cashflow trend" },
            { key: "categories", label: "Expense categories" },
            { key: "categoryTrend", label: "Category trend" },
            { key: "netWorth", label: "Net worth trend" },
            { key: "heatmap", label: "Spending heatmap" },
            { key: "merchants", label: "Top merchants" },
            { key: "budgets", label: "Budget overview" },
            { key: "accounts", label: "Account balances" },
          ].map((item) => (
            <Checkbox
              key={item.key}
              label={item.label}
              checked={Boolean(sectionVisibility[item.key])}
              onChange={(event) =>
                setSectionVisibility((current) => ({
                  ...current,
                  [item.key]: event.currentTarget.checked,
                }))
              }
            />
          ))}
          <Text size="xs" c="dimmed">
            Shortcuts: Ctrl/Cmd + Shift + A (quick add), Ctrl/Cmd + Shift + C (customize), Ctrl/Cmd
            + Shift + E (export CSV)
          </Text>
        </Stack>
      </Modal>
      </Stack>
    </Container>
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
      const [cashflowData, categoryData, netWorthData] = await Promise.all([
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
        apiFetch<NetWorthTrendResponse>(
          `/reporting/net-worth?from_date=${encodeURIComponent(
            dashboard.from_date,
          )}&to_date=${encodeURIComponent(dashboard.to_date)}&granularity=${granularity}`,
        ),
      ]);
      setCashflow(cashflowData);
      setCategories(categoryData);
      setNetWorth(netWorthData);

      const trendData = await apiFetch<CategoryTrendResponse>(
        `/reporting/category-trend?from_date=${encodeURIComponent(
          dashboard.from_date,
        )}&to_date=${encodeURIComponent(dashboard.to_date)}&granularity=${granularity}&breakdown_type=expense&limit=5`,
      );
      setCategoryTrend(trendData);

      try {
        const [heatmapData, merchantData] = await Promise.all([
          apiFetch<HeatmapResponse>(
            `/reporting/heatmap?from_date=${encodeURIComponent(
              dashboard.from_date,
            )}&to_date=${encodeURIComponent(dashboard.to_date)}&breakdown_type=expense`,
          ),
          apiFetch<MerchantSummaryResponse>(
            `/reporting/merchants?from_date=${encodeURIComponent(
              dashboard.from_date,
            )}&to_date=${encodeURIComponent(
              dashboard.to_date,
            )}&breakdown_type=expense&limit=8`,
          ),
        ]);
        setHeatmap(heatmapData);
        setMerchantSummary(merchantData);
      } catch {
        setHeatmap(null);
        setMerchantSummary(null);
      }

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
      notifications.show({
        title: "Export ready",
        message: "CSV download started.",
        color: "teal",
      });
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
      notifications.show({
        title: "Transaction added",
        message: "Your transaction is now recorded.",
        color: "teal",
      });
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

function buildHeatmapGrid(heatmap: HeatmapResponse | null): {
  weeks: Array<Array<{ key: string; amount: number; label: string }>>;
  max: number;
} {
  if (!heatmap) {
    return { weeks: [], max: 0 };
  }

  const amounts = new Map<string, number>();
  let max = 0;
  for (const point of heatmap.points) {
    const amount = toNumber(point.amount);
    amounts.set(point.date, amount);
    if (amount > max) {
      max = amount;
    }
  }

  const start = new Date(heatmap.from_date);
  const end = new Date(heatmap.to_date);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return { weeks: [], max };
  }

  const startDate = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), start.getUTCDate()));
  const endDate = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate()));
  if (
    end.getUTCHours() === 0 &&
    end.getUTCMinutes() === 0 &&
    end.getUTCSeconds() === 0 &&
    end.getUTCMilliseconds() === 0
  ) {
    endDate.setUTCDate(endDate.getUTCDate() - 1);
  }
  if (endDate < startDate) {
    return { weeks: [], max };
  }

  const days: Array<{ key: string; amount: number; label: string }> = [];
  const formatter = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" });
  for (
    let cursor = new Date(startDate);
    cursor <= endDate;
    cursor.setUTCDate(cursor.getUTCDate() + 1)
  ) {
    const key = cursor.toISOString().slice(0, 10);
    const amount = amounts.get(key) ?? 0;
    days.push({ key, amount, label: formatter.format(cursor) });
  }

  const weeks: Array<Array<{ key: string; amount: number; label: string }>> = [];
  for (let i = 0; i < days.length; i += 7) {
    weeks.push(days.slice(i, i + 7));
  }
  return { weeks, max };
}

function heatmapColor(amount: number, max: number): string {
  if (max <= 0 || amount <= 0) {
    return "#f1f3f5";
  }
  const intensity = Math.min(amount / max, 1);
  const lightness = 92 - intensity * 50;
  return `hsl(210, 60%, ${lightness}%)`;
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
