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
  amount: string;
  direction: TransactionDirection;
  signed_amount: string;
  merchant: string | null;
  note: string | null;
  occurred_at: string;
  created_at: string;
  updated_at: string;
}

export interface CreateTransactionRequest {
  account_id: string;
  amount: string;
  direction: TransactionDirection;
  occurred_at: string;
  merchant?: string;
  note?: string;
}

export type ReportPeriod = "day" | "week" | "month" | "year";
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
