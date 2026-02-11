export interface HealthResponse {
  status: string;
}

export interface ErrorResponse {
  code: string;
  message: string;
  details?: unknown;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthStatusResponse {
  status: string;
}

export interface UserResponse {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export type AccountType =
  | "CHECKING"
  | "SAVINGS"
  | "CREDIT_CARD"
  | "CASH"
  | "INVESTMENT";

export type TransactionDirection = "IN" | "OUT";

export interface AccountResponse {
  id: string;
  user_id: string;
  name: string;
  account_type: AccountType;
  currency: string;
  opening_balance: string;
  current_balance: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CategoryResponse {
  id: string;
  user_id: string;
  name: string;
  is_income: boolean;
  color: string | null;
  icon: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateCategoryRequest {
  name: string;
  is_income: boolean;
  color?: string | null;
  icon?: string | null;
}

export interface UpdateCategoryRequest {
  name?: string;
  is_income?: boolean;
  color?: string | null;
  icon?: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface CreateAccountRequest {
  name: string;
  account_type: AccountType;
  opening_balance: string;
  currency: string;
}

export interface UpdateAccountRequest {
  name?: string;
  account_type?: AccountType;
  currency?: string;
}

export interface AccountBalanceResponse {
  account_id: string;
  balance: string;
}

export interface TransactionResponse {
  id: string;
  account_id: string;
  category_id: string | null;
  transfer_id: string | null;
  amount: string;
  direction: TransactionDirection;
  signed_amount: string;
  merchant: string | null;
  note: string | null;
  tags: string[] | null;
  splits?: TransactionSplitResponse[] | null;
  attachments?: TransactionAttachmentResponse[] | null;
  occurred_at: string;
  created_at: string;
  updated_at: string;
}

export interface TransactionSplitRequest {
  category_id?: string | null;
  amount: string;
  note?: string | null;
}

export interface TransactionSplitResponse {
  id: string;
  category_id: string | null;
  amount: string;
  note: string | null;
  created_at: string;
}

export interface TransactionAttachmentResponse {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface CreateTransactionRequest {
  account_id: string;
  amount: string;
  direction: TransactionDirection;
  occurred_at: string;
  category_id?: string | null;
  merchant?: string;
  note?: string;
  tags?: string[] | null;
  splits?: TransactionSplitRequest[] | null;
}

export interface TransferCreateRequest {
  from_account_id: string;
  to_account_id: string;
  amount: string;
  occurred_at: string;
  note?: string | null;
}

export interface TransferResponse {
  transfer_id: string;
  outgoing: TransactionResponse;
  incoming: TransactionResponse;
}

export interface TransactionBulkCategoryRequest {
  transaction_ids: string[];
  category_id: string | null;
}

export interface TransactionBulkCategoryResponse {
  updated_count: number;
}

export interface TransactionImportError {
  row: number;
  message: string;
}

export interface TransactionImportResponse {
  imported: number;
  skipped: number;
  errors: TransactionImportError[];
}

export interface UpdateTransactionRequest {
  category_id?: string | null;
  amount?: string;
  direction?: TransactionDirection;
  occurred_at?: string;
  merchant?: string | null;
  note?: string | null;
  tags?: string[] | null;
  splits?: TransactionSplitRequest[] | null;
}

export type RecurringCadence = "DAILY" | "WEEKLY" | "MONTHLY";

export interface RecurringTransactionResponse {
  id: string;
  user_id: string;
  account_id: string;
  category_id: string | null;
  amount: string;
  direction: TransactionDirection;
  cadence: RecurringCadence;
  interval: number;
  start_at: string;
  next_run_at: string;
  end_at: string | null;
  merchant: string | null;
  note: string | null;
  tags: string[] | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RecurringTransactionListResponse {
  items: RecurringTransactionResponse[];
}

export interface RecurringRunResponse {
  created: number;
  skipped: number;
}

export interface RecurringTransactionCreateRequest {
  account_id: string;
  category_id?: string | null;
  amount: string;
  direction: TransactionDirection;
  cadence: RecurringCadence;
  interval?: number;
  start_at: string;
  end_at?: string | null;
  merchant?: string | null;
  note?: string | null;
  tags?: string[] | null;
}

export interface RecurringTransactionUpdateRequest {
  category_id?: string | null;
  amount?: string;
  direction?: TransactionDirection;
  cadence?: RecurringCadence;
  interval?: number;
  start_at?: string;
  end_at?: string | null;
  merchant?: string | null;
  note?: string | null;
  tags?: string[] | null;
  is_active?: boolean;
}

export type ReportPeriod = "day" | "week" | "month" | "year" | "custom";
export type ReportGranularity = "day" | "week" | "month";
export type CategoryBreakdownType = "expense" | "income";

export interface AccountBalanceSummaryItem {
  account_id: string;
  account_name: string;
  account_type: AccountType;
  currency: string;
  balance: string;
}

export interface DashboardSummaryResponse {
  period: ReportPeriod;
  from_date: string;
  to_date: string;
  income: string;
  expenses: string;
  net: string;
  total_balance: string;
  account_count: number;
  accounts: AccountBalanceSummaryItem[];
}

export interface CashflowPoint {
  period: string;
  income: string;
  expenses: string;
  net: string;
}

export interface CashflowTrendResponse {
  from_date: string;
  to_date: string;
  granularity: ReportGranularity;
  points: CashflowPoint[];
}

export interface CategoryBreakdownItem {
  category_id: string | null;
  category_name: string;
  color: string | null;
  icon: string | null;
  amount: string;
  percentage: number;
}

export interface CategoryBreakdownResponse {
  from_date: string;
  to_date: string;
  breakdown_type: CategoryBreakdownType;
  total: string;
  categories: CategoryBreakdownItem[];
}

export interface CategoryTrendPoint {
  period: string;
  category_id: string | null;
  category_name: string;
  color: string | null;
  icon: string | null;
  amount: string;
}

export interface CategoryTrendResponse {
  from_date: string;
  to_date: string;
  granularity: ReportGranularity;
  breakdown_type: CategoryBreakdownType;
  points: CategoryTrendPoint[];
}

export type BudgetStatus = "on_track" | "warning" | "exceeded";

export interface BudgetResponse {
  id: string;
  user_id: string;
  category_id: string;
  month: string;
  limit_amount: string;
  rollover_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface BudgetProgressItem {
  budget_id: string;
  category_id: string;
  category_name: string;
  category_color: string | null;
  category_icon: string | null;
  month: string;
  limit_amount: string;
  effective_limit: string;
  rollover_amount: string;
  rollover_enabled: boolean;
  spent_amount: string;
  remaining_amount: string;
  percentage_used: number;
  status: BudgetStatus;
  days_elapsed: number;
  days_remaining: number;
  daily_average: string;
  projected_spend: string;
  projected_diff: string;
}

export interface BudgetProgressResponse {
  month: string;
  items: BudgetProgressItem[];
}

export interface CreateBudgetRequest {
  category_id: string;
  month: string;
  limit_amount: string;
  rollover_enabled?: boolean;
}

export interface UpdateBudgetRequest {
  limit_amount: string;
  rollover_enabled?: boolean;
}

export interface CopyBudgetsResponse {
  source_month: string;
  target_month: string;
  created_count: number;
}

export interface BudgetSummaryItem {
  month: string;
  budgeted: string;
  spent: string;
  variance: string;
}

export interface BudgetSummaryResponse {
  items: BudgetSummaryItem[];
}
