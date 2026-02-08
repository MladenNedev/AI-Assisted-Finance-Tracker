import {
    Button,
    Paper,
    PasswordInput,
    Stack,
    Text,
    TextInput,
    Title
  } from "@mantine/core";
  
  type LoginProps = {
    onSuccess?: () => void;
  };
  
  export default function Login({ onSuccess }: LoginProps) {
    return (
      <Stack align="center" mt="xl">
        <Paper withBorder shadow="sm" radius="md" p="xl" w={360}>
          <Stack>
            <Title order={3}>Sign in</Title>
            <Text c="dimmed" size="sm">
              Use your internal account. Auth flow is coming in Phase 1.
            </Text>
            <TextInput label="Email" placeholder="you@company.com" />
            <PasswordInput label="Password" placeholder="••••••••" />
            <Button onClick={onSuccess}>Continue</Button>
          </Stack>
        </Paper>
      </Stack>
    );
  }
  