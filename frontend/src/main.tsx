import React from "react";
import ReactDOM from "react-dom/client";
import {
  MantineProvider,
  createTheme,
  localStorageColorSchemeManager,
} from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { BrowserRouter } from "react-router-dom";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import App from "./App";
import "./styles.css";

const theme = createTheme({
  fontFamily: "Space Grotesk, sans-serif",
  primaryColor: "teal"
});

const colorSchemeManager = localStorageColorSchemeManager({
  key: "finance-color-scheme",
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MantineProvider
      theme={theme}
      defaultColorScheme="light"
      colorSchemeManager={colorSchemeManager}
    >
      <Notifications position="top-right" />
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </MantineProvider>
  </React.StrictMode>
);
