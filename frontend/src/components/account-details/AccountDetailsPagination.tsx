import { Group, Pagination } from "@mantine/core";

type AccountDetailsPaginationProps = {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
};

export default function AccountDetailsPagination({
  page,
  totalPages,
  onChange,
}: AccountDetailsPaginationProps) {
  return (
    <Group justify="center">
      <Pagination value={page} onChange={onChange} total={totalPages} />
    </Group>
  );
}
