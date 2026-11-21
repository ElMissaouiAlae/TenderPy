import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { Layout } from "./components/Layout";
import { TenderDetailPage } from "./pages/TenderDetailPage";
import { TenderListPage } from "./pages/TenderListPage";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/tenders" replace />} />
          <Route path="tenders" element={<TenderListPage />} />
          <Route path="tenders/:id" element={<TenderDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
