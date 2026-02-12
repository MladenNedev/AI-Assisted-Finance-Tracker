import { Alert } from "@mantine/core";

type AccountErrorBannerProps = {
  error: string | null;
};

export default function AccountErrorBanner({ error }: AccountErrorBannerProps) {
  if (!error) {
    return null;
  }
  return (
    <Alert color="red" title="Failed to load account">
      {error}
    </Alert>
  );
}
