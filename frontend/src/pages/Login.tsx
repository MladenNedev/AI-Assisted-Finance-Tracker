import { useState } from "react";
import {
  Anchor,
  Button,
  Paper,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../contexts/AuthContext";

export default function Login() {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const demoEmail = import.meta.env.VITE_DEMO_EMAIL;
  const demoPassword = import.meta.env.VITE_DEMO_PASSWORD;
  const hasDemoCredentials = Boolean(demoEmail && demoPassword);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await handleAuth(async () => {
      if (isRegisterMode) {
        await register({ email, password });
      }
      await login({ email, password });
    });
  };

  const onDemoLogin = async () => {
    if (!demoEmail || !demoPassword) {
      return;
    }
    setIsRegisterMode(false);
    setEmail(demoEmail);
    setPassword(demoPassword);
    await handleAuth(() => login({ email: demoEmail, password: demoPassword }));
  };

  const handleAuth = async (action: () => Promise<void>) => {
    setErrorMessage(null);
    setSubmitting(true);
    try {
      await action();
      navigate("/dashboard", { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(`Authentication failed (HTTP ${error.status})`);
      } else {
        setErrorMessage("Authentication failed");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Stack align="center" mt="xl">
      <Paper withBorder shadow="sm" radius="md" p="xl" w={360}>
        <form onSubmit={onSubmit}>
          <Stack>
            <Title order={3}>{isRegisterMode ? "Create account" : "Sign in"}</Title>
            <Text c="dimmed" size="sm">
              Internal access only. Cookie sessions are enabled.
            </Text>
            <TextInput
              label="Email"
              placeholder="you@company.com"
              value={email}
              onChange={(event) => setEmail(event.currentTarget.value)}
              required
            />
            <PasswordInput
              label="Password"
              placeholder="At least 8 characters, letters and numbers"
              value={password}
              onChange={(event) => setPassword(event.currentTarget.value)}
              required
            />
            {errorMessage && (
              <Text c="red" size="sm">
                {errorMessage}
              </Text>
            )}
            <Button type="submit" loading={submitting}>
              {isRegisterMode ? "Register and sign in" : "Sign in"}
            </Button>
            {hasDemoCredentials ? (
              <Button variant="light" onClick={onDemoLogin} disabled={submitting}>
                Try demo account
              </Button>
            ) : null}
            <Anchor
              component="button"
              type="button"
              size="sm"
              onClick={() => setIsRegisterMode((current) => !current)}
            >
              {isRegisterMode
                ? "Already have an account? Sign in"
                : "Need an account? Register"}
            </Anchor>
          </Stack>
        </form>
      </Paper>
    </Stack>
  );
}
