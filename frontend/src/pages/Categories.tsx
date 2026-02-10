import { useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";

import { ApiError, apiFetch } from "../api/client";
import type {
  CategoryResponse,
  CreateCategoryRequest,
  PaginatedResponse,
  UpdateCategoryRequest,
} from "../api/types";

const PAGE_LIMIT = 500;

type CategoryFormState = {
  name: string;
  is_income: boolean;
  color: string;
  icon: string;
};

const INITIAL_FORM: CategoryFormState = {
  name: "",
  is_income: false,
  color: "#2E86AB",
  icon: "",
};

export default function Categories() {
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingCategory, setEditingCategory] = useState<CategoryResponse | null>(null);
  const [form, setForm] = useState<CategoryFormState>(INITIAL_FORM);

  useEffect(() => {
    void loadCategories();
  }, []);

  const onOpenCreate = () => {
    setEditingCategory(null);
    setForm(INITIAL_FORM);
    setOpened(true);
  };

  const onOpenEdit = (category: CategoryResponse) => {
    setEditingCategory(category);
    setForm({
      name: category.name,
      is_income: category.is_income,
      color: category.color ?? "#2E86AB",
      icon: category.icon ?? "",
    });
    setOpened(true);
  };

  const onSubmit = async () => {
    if (!form.name.trim()) {
      setError("Category name is required");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      if (editingCategory) {
        const payload: UpdateCategoryRequest = {
          name: form.name.trim(),
          is_income: form.is_income,
          color: normalizeColor(form.color),
          icon: normalizeIcon(form.icon),
        };
        await apiFetch<CategoryResponse>(`/categories/${editingCategory.id}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        const payload: CreateCategoryRequest = {
          name: form.name.trim(),
          is_income: form.is_income,
          color: normalizeColor(form.color),
          icon: normalizeIcon(form.icon),
        };
        await apiFetch<CategoryResponse>("/categories", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }

      setOpened(false);
      setForm(INITIAL_FORM);
      setEditingCategory(null);
      await loadCategories();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const onDelete = async (category: CategoryResponse) => {
    const confirmed = window.confirm(
      `Delete category "${category.name}"? Existing transactions will become uncategorized.`,
    );
    if (!confirmed) {
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await apiFetch<void>(`/categories/${category.id}`, { method: "DELETE" });
      await loadCategories();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Stack mt="md" gap="md">
      <Group justify="space-between">
        <Title order={2}>Categories</Title>
        <Group>
          <Text c="dimmed" size="sm">
            {total} total
          </Text>
          <Button onClick={onOpenCreate}>Add category</Button>
        </Group>
      </Group>

      {error ? (
        <Alert color="red" title="Category request failed">
          {error}
        </Alert>
      ) : null}

      <Table striped highlightOnHover withTableBorder>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Type</Table.Th>
            <Table.Th>Color</Table.Th>
            <Table.Th ta="right">Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {categories.map((category) => (
            <Table.Tr key={category.id}>
              <Table.Td>
                <Group gap="xs">
                  {category.icon ? <span>{category.icon}</span> : null}
                  <Text>{category.name}</Text>
                </Group>
              </Table.Td>
              <Table.Td>
                <Badge color={category.is_income ? "teal" : "orange"}>
                  {category.is_income ? "Income" : "Expense"}
                </Badge>
              </Table.Td>
              <Table.Td>
                {category.color ? (
                  <div
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: 4,
                      border: "1px solid #CED4DA",
                      backgroundColor: category.color,
                    }}
                  />
                ) : (
                  <Text size="sm" c="dimmed">
                    None
                  </Text>
                )}
              </Table.Td>
              <Table.Td>
                <Group justify="flex-end" gap="xs">
                  <Button size="xs" variant="subtle" onClick={() => onOpenEdit(category)}>
                    Edit
                  </Button>
                  <Button
                    size="xs"
                    variant="subtle"
                    color="red"
                    onClick={() => onDelete(category)}
                    loading={submitting}
                  >
                    Delete
                  </Button>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
          {!loading && categories.length === 0 ? (
            <Table.Tr>
              <Table.Td colSpan={4}>
                <Text ta="center" c="dimmed">
                  No categories yet.
                </Text>
              </Table.Td>
            </Table.Tr>
          ) : null}
        </Table.Tbody>
      </Table>

      <Modal
        opened={opened}
        onClose={() => setOpened(false)}
        title={editingCategory ? "Edit category" : "Create category"}
        centered
      >
        <Stack>
          <TextInput
            label="Name"
            placeholder="Food, Rent, Salary"
            value={form.name}
            onChange={(event) =>
              setForm((current) => ({ ...current, name: event.currentTarget.value }))
            }
            required
          />
          <Select
            label="Type"
            value={form.is_income ? "income" : "expense"}
            onChange={(value) =>
              setForm((current) => ({ ...current, is_income: value === "income" }))
            }
            data={[
              { value: "expense", label: "Expense" },
              { value: "income", label: "Income" },
            ]}
          />
          <TextInput
            label="Color"
            type="color"
            value={form.color}
            onChange={(event) =>
              setForm((current) => ({ ...current, color: event.currentTarget.value }))
            }
          />
          <TextInput
            label="Icon (optional)"
            placeholder="e.g. 🍔"
            value={form.icon}
            onChange={(event) =>
              setForm((current) => ({ ...current, icon: event.currentTarget.value }))
            }
          />
          <Button onClick={onSubmit} loading={submitting}>
            {editingCategory ? "Update category" : "Create category"}
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );

  async function loadCategories() {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch<PaginatedResponse<CategoryResponse>>(
        `/categories?limit=${PAGE_LIMIT}&offset=0`,
      );
      setCategories(response.items);
      setTotal(response.total);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }
}

function normalizeColor(value: string): string | null {
  const color = value.trim();
  if (!color) {
    return null;
  }
  return color;
}

function normalizeIcon(value: string): string | null {
  const icon = value.trim();
  if (!icon) {
    return null;
  }
  return icon;
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
