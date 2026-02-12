import { Button, Group, Title } from "@mantine/core";
import { Link } from "react-router-dom";

export default function AccountDetailsHeader() {
  return (
    <Group justify="space-between" align="center">
      <Title order={2}>Account Details</Title>
      <Button component={Link} to="/accounts" variant="subtle">
        Back to accounts
      </Button>
    </Group>
  );
}
