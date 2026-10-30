import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const mocks = vi.hoisted(() => ({
  observer: null,
  onIdTokenChanged: vi.fn((auth, callback) => { mocks.observer = callback; queueMicrotask(() => callback(mocks.currentUser)); return () => {}; }),
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
  currentUser: { email: "admin@example.test", getIdToken: vi.fn() },
  adminMe: vi.fn(),
}));
vi.mock("@firebase/auth", () => ({ onIdTokenChanged: mocks.onIdTokenChanged, signInWithPopup: mocks.signInWithPopup, signOut: mocks.signOut }));
vi.mock("../auth/firebase", () => ({ firebaseAuth: {}, firebaseConfigurationReady: true, googleProvider: {} }));
vi.mock("../services/api", () => ({ api: { adminMe: mocks.adminMe } }));

import { AuthProvider, useAuth } from "../auth/AuthContext";

function Probe() {
  const { user, admin, signIn, logout } = useAuth();
  return <div><span>{user?.email || "signed out"}</span><span>{admin?.email || "no admin"}</span><button onClick={signIn}>Sign in</button><button onClick={logout}>Sign out</button></div>;
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.currentUser = { email: "admin@example.test", getIdToken: vi.fn() };
  mocks.adminMe.mockResolvedValue({ email: "admin@example.test", active: true, permissions: ["dashboard.read"] });
  mocks.signInWithPopup.mockResolvedValue({});
  mocks.signOut.mockImplementation(() => {
    mocks.currentUser = null;
    mocks.observer?.(null);
    return Promise.resolve();
  });
});

describe("Firebase session observer", () => {
  it("restores the Firebase session and verifies permissions with the backend", async () => {
    render(<AuthProvider><Probe /></AuthProvider>);
    expect((await screen.findAllByText("admin@example.test")).length).toBe(2);
    await waitFor(() => expect(mocks.adminMe).toHaveBeenCalledWith(mocks.currentUser));
  });

  it("uses Google popup sign-in and Firebase logout", async () => {
    render(<AuthProvider><Probe /></AuthProvider>);
    fireEvent.click(await screen.findByRole("button", { name: "Sign in" }));
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    await waitFor(() => expect(mocks.signInWithPopup).toHaveBeenCalledOnce());
    expect(mocks.signOut).toHaveBeenCalledOnce();
    expect(await screen.findByText("signed out")).toBeInTheDocument();
    expect(screen.getByText("no admin")).toBeInTheDocument();
  });
});
