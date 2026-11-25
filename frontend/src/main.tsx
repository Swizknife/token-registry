import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import DisplayPage from "./routes/display/DisplayPage";
import KioskPage from "./routes/kiosk/KioskPage";
import StaffApp from "./routes/staff/StaffApp";

import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/kiosk" replace />} />
        <Route path="/kiosk" element={<KioskPage />} />
        <Route path="/display" element={<DisplayPage />} />
        <Route path="/staff/*" element={<StaffApp />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
