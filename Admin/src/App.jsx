import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequireAdmin } from "./auth/RequireAdmin";
import { AppShell } from "./components/AppShell";
import { StatePanel } from "./components/StatePanel";

const LoginPage = lazy(() => import("./pages/LoginPage").then((module) => ({ default: module.LoginPage })));
const DashboardPage = lazy(() => import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const PeopleListPage = lazy(() => import("./pages/PeoplePages").then((module) => ({ default: module.PeopleListPage })));
const PersonDetailPage = lazy(() => import("./pages/PeoplePages").then((module) => ({ default: module.PersonDetailPage })));
const JobsPage = lazy(() => import("./pages/JobsPage").then((module) => ({ default: module.JobsPage })));
const JobDetailPage = lazy(() => import("./pages/JobsPage").then((module) => ({ default: module.JobDetailPage })));
const SettingsPage = lazy(() => import("./pages/SecondaryPages").then((module) => ({ default: module.SettingsPage })));
const SystemHealthPage = lazy(() => import("./pages/SecondaryPages").then((module) => ({ default: module.SystemHealthPage })));
const UnavailablePage = lazy(() => import("./pages/SecondaryPages").then((module) => ({ default: module.UnavailablePage })));

function UnauthorizedPage() {
  const { logout, user } = useAuth();
  return <div className="unauthorized-screen"><StatePanel tone="denied" title="Administrator access required" detail={`The signed-in account ${user?.email ? `(${user.email}) ` : ""}does not have an active server-managed Admin permission. Ask an ERRNO operator to provision access.`} actionLabel="Sign out" onAction={logout} /></div>;
}

function RouteTree() {
  return <Suspense fallback={<div className="auth-loading">Loading workspace…</div>}><Routes>
    <Route path="/admin/login" element={<LoginPage />} />
    <Route path="/admin/unauthorized" element={<UnauthorizedPage />} />
    <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />
    <Route path="/admin" element={<RequireAdmin><AppShell /></RequireAdmin>}>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="dashboard" element={<DashboardPage />} />
      <Route path="shop-owners" element={<PeopleListPage kind="shop-owners" />} />
      <Route path="shop-owners/:userId" element={<PersonDetailPage kind="shop-owners" />} />
      <Route path="workers" element={<PeopleListPage kind="workers" />} />
      <Route path="workers/:userId" element={<PersonDetailPage kind="workers" />} />
      <Route path="jobs" element={<JobsPage />} />
      <Route path="jobs/:jobId" element={<JobDetailPage />} />
      <Route path="bookings" element={<UnavailablePage name="Bookings" />} />
      <Route path="categories" element={<UnavailablePage name="Categories" />} />
      <Route path="attendance" element={<UnavailablePage name="Attendance" />} />
      <Route path="ratings" element={<UnavailablePage name="Ratings" />} />
      <Route path="disputes" element={<UnavailablePage name="Disputes" />} />
      <Route path="notifications" element={<UnavailablePage name="Notifications" />} />
      <Route path="system-health" element={<SystemHealthPage />} />
      <Route path="settings" element={<SettingsPage />} />
    </Route>
    <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
  </Routes></Suspense>;
}

export default function App() {
  return <AuthProvider><BrowserRouter><RouteTree /></BrowserRouter></AuthProvider>;
}
