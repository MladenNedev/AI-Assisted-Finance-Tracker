import { useEffect, useMemo, useState } from "react";

import { ApiError, apiFetch } from "../api/client";
import type {
  AccountResponse,
  CategoryResponse,
  PaginatedResponse,
  TransactionResponse,
} from "../api/types";

const PAGE_LIMIT = 20;

type UseAccountDetailsDataResult = {
  account: AccountResponse | null;
  transactions: TransactionResponse[];
  categories: CategoryResponse[];
  categoryLookup: Map<string, CategoryResponse>;
  page: number;
  setPage: (page: number) => void;
  totalPages: number;
  loading: boolean;
  error: string | null;
};

export function useAccountDetailsData(
  accountId: string | undefined,
): UseAccountDetailsDataResult {
  const [account, setAccount] = useState<AccountResponse | null>(null);
  const [transactions, setTransactions] = useState<TransactionResponse[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [accountLoading, setAccountLoading] = useState(false);
  const [transactionsLoading, setTransactionsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const categoryLookup = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories],
  );

  useEffect(() => {
    if (!accountId) {
      setError("Account id missing from route");
      setAccountLoading(false);
      setTransactionsLoading(false);
      return;
    }
    setPage(1);
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
  const loading = accountLoading || transactionsLoading;

  return {
    account,
    transactions,
    categories,
    categoryLookup,
    page,
    setPage,
    totalPages,
    loading,
    error,
  };

  async function loadAccount(id: string) {
    setAccountLoading(true);
    setError(null);
    try {
      const response = await apiFetch<AccountResponse>(`/accounts/${id}`);
      setAccount(response);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setAccountLoading(false);
    }
  }

  async function loadTransactions(id: string, targetPage: number) {
    setTransactionsLoading(true);
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
      setTransactionsLoading(false);
    }
  }

  async function loadCategories() {
    setError(null);
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
