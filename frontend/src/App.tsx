import { AppShell, Button, Group, Menu, Text } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import Accounts from "./pages/Accounts";
import AccountDetails from "./pages/AccountDetails";
import Budgets from "./pages/Budgets";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Categories from "./pages/Categories";
import Transactions from "./pages/Transactions";
import Recurring from "./pages/Recurring";

const NAV_ITEMS = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Accounts", to: "/accounts" },
  { label: "Transactions", to: "/transactions" },
  { label: "Categories", to: "/categories" },
  { label: "Budgets", to: "/budgets" },
  { label: "Recurring", to: "/recurring" },
] as const;

function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const isCompactNav = useMediaQuery("(max-width: 760px)") ?? false;
  const isStackedHeader = useMediaQuery("(max-width: 1035px)") ?? false;
  const headerHeight =
    user && (isCompactNav || isStackedHeader) ? (isCompactNav ? 72 : 96) : 56;
  const showInlineNav = user && !isCompactNav;

  return (
    <AppShell padding="md" header={{ height: headerHeight }}>
      <AppShell.Header>
        <HeaderNav
          userEmail={user?.email}
          navItems={NAV_ITEMS}
          isCompactNav={isCompactNav}
          isStackedHeader={isStackedHeader}
          showInlineNav={showInlineNav}
          locationPath={location.pathname}
          logout={logout}
        />
      </AppShell.Header>
      <AppShell.Main>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/accounts"
            element={
              <ProtectedRoute>
                <Accounts />
              </ProtectedRoute>
            }
          />
          <Route
            path="/accounts/:accountId"
            element={
              <ProtectedRoute>
                <AccountDetails />
              </ProtectedRoute>
            }
          />
          <Route
            path="/budgets"
            element={
              <ProtectedRoute>
                <Budgets />
              </ProtectedRoute>
            }
          />
          <Route
            path="/transactions"
            element={
              <ProtectedRoute>
                <Transactions />
              </ProtectedRoute>
            }
          />
          <Route
            path="/categories"
            element={
              <ProtectedRoute>
                <Categories />
              </ProtectedRoute>
            }
          />
          <Route
            path="/recurring"
            element={
              <ProtectedRoute>
                <Recurring />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}

type NavItem = { label: string; to: string };

type HeaderNavProps = {
  userEmail?: string;
  navItems: ReadonlyArray<NavItem>;
  isCompactNav: boolean;
  isStackedHeader: boolean;
  showInlineNav: boolean;
  locationPath: string;
  logout: () => Promise<void> | void;
};

function HeaderNav({
  userEmail,
  navItems,
  isCompactNav,
  isStackedHeader,
  showInlineNav,
  locationPath,
  logout,
}: HeaderNavProps) {
  return (
    <Group
      h="100%"
      px="md"
      py="xs"
      justify="space-between"
      align="center"
      wrap="wrap"
    >
      <Group gap="sm" wrap="wrap" style={{ flex: 1 }}>
        <Text fw={700}>Capital Flow</Text>
        {userEmail && showInlineNav ? (
          <Group gap="xs" wrap="wrap">
            {navItems.map((item) => (
              <Button
                key={item.to}
                component={Link}
                to={item.to}
                size="xs"
                variant={locationPath.startsWith(item.to) ? "light" : "subtle"}
              >
                {item.label}
              </Button>
            ))}
            <Button size="xs" variant="light" onClick={logout}>
              Logout
            </Button>
          </Group>
        ) : null}
      </Group>
      <Group
        gap="sm"
        align="center"
        wrap="wrap"
        w={isCompactNav ? undefined : isStackedHeader ? "100%" : undefined}
      >
        {userEmail && isCompactNav ? (
          <Menu shadow="md" width={200} position="bottom-end">
            <Menu.Target>
              <Button size="xs" variant="light">
                Menu
              </Button>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Label>{userEmail}</Menu.Label>
              {navItems.map((item) => (
                <Menu.Item key={item.to} component={Link} to={item.to}>
                  {item.label}
                </Menu.Item>
              ))}
              <Menu.Item onClick={logout}>Logout</Menu.Item>
            </Menu.Dropdown>
          </Menu>
        ) : null}
        {!isCompactNav ? (
          <Text size="sm" c="dimmed" lineClamp={1} maw={220} title={userEmail}>
            {userEmail ?? "Not signed in"}
          </Text>
        ) : null}
      </Group>
    </Group>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppLayout />
    </AuthProvider>
  );
}
