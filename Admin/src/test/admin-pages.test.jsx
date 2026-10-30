import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

const { useAuth, api } = vi.hoisted(() => ({
  useAuth: vi.fn(),
  api: {
    dashboard: vi.fn(), workers: vi.fn(), shopOwners: vi.fn(), worker: vi.fn(), shopOwner: vi.fn(),
    jobs: vi.fn(), updateJobStatus: vi.fn(), updateWorker: vi.fn(), updateShopOwner: vi.fn(),
  },
}));
vi.mock("../auth/AuthContext", () => ({ useAuth: () => useAuth(), AuthProvider: ({ children }) => children }));
vi.mock("../services/api", () => ({ api }));

import { LoginPage } from "../pages/LoginPage";
import { DashboardPage } from "../pages/DashboardPage";
import { PersonDetailPage, PeopleListPage } from "../pages/PeoplePages";
import { JobsPage } from "../pages/JobsPage";
import { RequireAdmin } from "../auth/RequireAdmin";

const user = { email: "admin@example.test", getIdToken: vi.fn() };
const admin = { email: "admin@example.test", active: true, permissions: ["dashboard.read", "users.read", "users.manage", "jobs.read", "jobs.manage"] };

beforeEach(() => {
  vi.clearAllMocks();
  useAuth.mockReturnValue({ user, admin, authLoading: false, adminLoading: false, adminError: null, authError: "", signIn: vi.fn(), logout: vi.fn(), retryAdminCheck: vi.fn() });
});

describe("admin authentication gates and live pages", () => {
  it("starts Google sign-in from the login screen", async () => {
    const signIn = vi.fn().mockResolvedValue(undefined);
    useAuth.mockReturnValue({ ...useAuth(), user: null, admin: null, signIn });
    render(<MemoryRouter><LoginPage /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: /continue with google/i }));
    await waitFor(() => expect(signIn).toHaveBeenCalledOnce());
  });

  it("renders explicit denial when the backend rejects admin permission", () => {
    const logout = vi.fn();
    useAuth.mockReturnValue({ ...useAuth(), admin: null, adminError: { status: 403 }, logout });
    render(<MemoryRouter initialEntries={["/admin/dashboard"]}><Routes><Route path="/admin/dashboard" element={<RequireAdmin><div>Protected content</div></RequireAdmin>} /></Routes></MemoryRouter>);
    expect(screen.getByText("Administrator access required")).toBeInTheDocument();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("renders dashboard metrics from the backend response", async () => {
    api.dashboard.mockResolvedValue({
      metrics: { total_users: 18, total_workers: 11, total_shop_owners: 7, total_shops: 6, total_jobs: 9, active_jobs: 4, completed_jobs: 3, total_applications: 12 },
      registrations_by_day: [], jobs_by_day: [], recent_registrations: [], recent_jobs: [],
    });
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(await screen.findByText("18")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(api.dashboard).toHaveBeenCalledWith(user, expect.any(AbortSignal));
  });

  it("shows a retryable API error instead of seeded metrics", async () => {
    api.dashboard.mockRejectedValue(new Error("API offline"));
    render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(await screen.findByText("Dashboard data is unavailable")).toBeInTheDocument();
    expect(screen.queryByText("1,284")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(api.dashboard).toHaveBeenCalledTimes(2));
  });

  it("shows loading and empty dashboard states without inventing records", async () => {
    let resolveDashboard;
    api.dashboard.mockReturnValue(new Promise((resolve) => { resolveDashboard = resolve; }));
    const { rerender } = render(<MemoryRouter><DashboardPage /></MemoryRouter>);
    expect(screen.getByLabelText("Loading data")).toBeInTheDocument();
    resolveDashboard({
      metrics: { total_users: 0, total_workers: 0, total_shop_owners: 0, total_shops: 0, total_jobs: 0, active_jobs: 0, completed_jobs: 0, total_applications: 0 },
      registrations_by_day: [], jobs_by_day: [], recent_registrations: [], recent_jobs: [],
    });
    expect(await screen.findByText("No user records yet.")).toBeInTheDocument();
    expect(screen.getByText("No job records yet.")).toBeInTheDocument();
    rerender(<MemoryRouter><DashboardPage /></MemoryRouter>);
  });

  it("loads shop owners with server-side search and pagination", async () => {
    api.shopOwners.mockResolvedValue({ items: [{ id: "u-1", name: "Asha Owner", email: "asha@example.test", shop_count: 2, job_count: 3, created_at: null, is_active: true }], total: 1, limit: 20, offset: 0 });
    render(<MemoryRouter><PeopleListPage kind="shop-owners" /></MemoryRouter>);
    expect(await screen.findByText("Asha Owner")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: /search shop owners/i }), { target: { value: "Asha" } });
    await waitFor(() => expect(api.shopOwners).toHaveBeenLastCalledWith(user, expect.objectContaining({ q: "Asha" }), expect.any(AbortSignal)));
    fireEvent.change(screen.getByRole("combobox", { name: "Account status" }), { target: { value: "false" } });
    await waitFor(() => expect(api.shopOwners).toHaveBeenLastCalledWith(user, expect.objectContaining({ q: "Asha", active: "false" }), expect.any(AbortSignal)));
  });

  it("loads worker rows from the backend", async () => {
    api.workers.mockResolvedValue({ items: [{ id: "worker-1", name: "Nisha Worker", email: "nisha@example.test", application_count: 4, created_at: null, is_active: true }], total: 1, limit: 20, offset: 0 });
    render(<MemoryRouter><PeopleListPage kind="workers" /></MemoryRouter>);
    expect(await screen.findByText("Nisha Worker")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(api.workers).toHaveBeenCalledWith(user, expect.objectContaining({ limit: 20, offset: 0 }), expect.any(AbortSignal));
  });

  it.each([
    ["shop owner", "shop-owners", "u-owner", "Asha Owner", "shopOwner", "updateShopOwner",
      { user: { id: "u-owner", name: "Asha Owner", is_active: true }, shops: [], jobs: [], jobs_truncated: false }],
    ["worker", "workers", "u-worker", "Nisha Worker", "worker", "updateWorker",
      { user: { id: "u-worker", name: "Nisha Worker", is_active: true }, applications: [], total_applications: 0, limit: 50, offset: 0 }],
  ])("sends %s management action to the API", async (_label, route, id, name, detailMethod, updateMethod, detail) => {
    api[detailMethod].mockResolvedValue(detail);
    api[updateMethod].mockResolvedValue({ is_active: false });
    render(<MemoryRouter initialEntries={[`/admin/${route}/${id}`]}><Routes>
      <Route path={`/admin/${route}/:userId`} element={<PersonDetailPage kind={route} />} />
    </Routes></MemoryRouter>);
    expect(await screen.findByRole("heading", { name })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Suspend account" }));
    await waitFor(() => expect(api[updateMethod]).toHaveBeenCalledWith(user, id, false));
  });

  it("updates a job through the admin API", async () => {
    api.jobs.mockResolvedValue({ items: [{ id: "j-1", title: "Packing shift", shop_name: "Market", owner_name: "Ravi", status: "open", application_count: 2, created_at: null }], total: 1, limit: 20, offset: 0 });
    api.updateJobStatus.mockResolvedValue({ status: "cancelled" });
    render(<MemoryRouter><JobsPage /></MemoryRouter>);
    expect(await screen.findByText("Packing shift")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: "Change status for Packing shift" }), { target: { value: "cancelled" } });
    await waitFor(() => expect(api.updateJobStatus).toHaveBeenCalledWith(user, "j-1", "cancelled"));
  });
});
