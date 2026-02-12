import { Stack, Table, Text } from "@mantine/core";

import ResponsiveTable from "../ResponsiveTable";
import { formatDateTime } from "../../utils/date";
import type { CategoryResponse, TransactionResponse } from "../../api/types";

type AccountTransactionsTableProps = {
  transactions: TransactionResponse[];
  categoryLookup: Map<string, CategoryResponse>;
  loading: boolean;
};

export default function AccountTransactionsTable({
  transactions,
  categoryLookup,
  loading,
}: AccountTransactionsTableProps) {
  return (
    <ResponsiveTable minWidth={700}>
      <Table striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Date</Table.Th>
            <Table.Th>Description</Table.Th>
            <Table.Th>Category</Table.Th>
            <Table.Th ta="right">Amount</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {transactions.map((transaction) => {
            const category = transaction.category_id
              ? categoryLookup.get(transaction.category_id)
              : null;
            return (
              <Table.Tr key={transaction.id}>
                <Table.Td>{formatDateTime(transaction.occurred_at)}</Table.Td>
                <Table.Td>
                  <Stack gap={0}>
                    <Text>{transaction.merchant ?? "No description"}</Text>
                    {transaction.note ? (
                      <Text size="xs" c="dimmed">
                        {transaction.note}
                      </Text>
                    ) : null}
                  </Stack>
                </Table.Td>
                <Table.Td>
                  {category ? (
                    <Text>
                      {category.icon ? `${category.icon} ` : ""}
                      {category.name}
                    </Text>
                  ) : (
                    <Text c="dimmed">Uncategorized</Text>
                  )}
                </Table.Td>
                <Table.Td ta="right">
                  <Text c={transaction.direction === "IN" ? "teal" : "red"} fw={600}>
                    {transaction.direction === "IN" ? "+" : "-"}${transaction.amount}
                  </Text>
                </Table.Td>
              </Table.Tr>
            );
          })}
          {!loading && transactions.length === 0 ? (
            <Table.Tr>
              <Table.Td colSpan={4}>
                <Text c="dimmed" ta="center">
                  No transactions for this account yet.
                </Text>
              </Table.Td>
            </Table.Tr>
          ) : null}
        </Table.Tbody>
      </Table>
    </ResponsiveTable>
  );
}
