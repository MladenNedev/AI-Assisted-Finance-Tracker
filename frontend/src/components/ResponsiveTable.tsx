import type { ReactNode } from "react";
import { Box, ScrollArea } from "@mantine/core";

type ResponsiveTableProps = {
  children: ReactNode;
  minWidth?: number;
};

export default function ResponsiveTable({
  children,
  minWidth = 720,
}: ResponsiveTableProps) {
  return (
    <ScrollArea type="auto" offsetScrollbars scrollbarSize={6}>
      <Box miw={minWidth}>{children}</Box>
    </ScrollArea>
  );
}
