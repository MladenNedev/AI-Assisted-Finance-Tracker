import { Stack } from "@mantine/core";
import { useParams } from "react-router-dom";

import AccountDetailsHeader from "../components/account-details/AccountDetailsHeader";
import AccountDetailsPagination from "../components/account-details/AccountDetailsPagination";
import AccountErrorBanner from "../components/account-details/AccountErrorBanner";
import AccountSummaryCard from "../components/account-details/AccountSummaryCard";
import AccountTransactionsTable from "../components/account-details/AccountTransactionsTable";
import { useAccountDetailsData } from "../hooks/useAccountDetailsData";

export default function AccountDetails() {
  const { accountId } = useParams();
  const {
    account,
    transactions,
    categoryLookup,
    page,
    setPage,
    totalPages,
    loading,
    error,
  } = useAccountDetailsData(accountId);

  return (
    <Stack mt="md" gap="md">
      <AccountDetailsHeader />
      <AccountErrorBanner error={error} />
      <AccountSummaryCard account={account} />

      <AccountTransactionsTable
        transactions={transactions}
        categoryLookup={categoryLookup}
        loading={loading}
      />

      <AccountDetailsPagination
        page={page}
        totalPages={totalPages}
        onChange={setPage}
      />
    </Stack>
  );
}
