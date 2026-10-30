import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../services/api";

beforeEach(() => vi.restoreAllMocks());

describe("authenticated API client", () => {
  it("attaches a Firebase ID token and never requests cookie credentials", async () => {
    const user = { getIdToken: vi.fn().mockResolvedValue("signed-id-token") };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ active: true }) }));
    await api.adminMe(user);
    const [, options] = fetch.mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer signed-id-token");
    expect(options.credentials).toBe("omit");
    expect(user.getIdToken).toHaveBeenCalledWith(false);
  });

  it("refreshes the token once after a 401", async () => {
    const user = { getIdToken: vi.fn().mockResolvedValueOnce("expired").mockResolvedValueOnce("refreshed") };
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({ detail: "expired" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ active: true }) }));
    await expect(api.adminMe(user)).resolves.toEqual({ active: true });
    expect(user.getIdToken.mock.calls).toEqual([[false], [true]]);
  });

  it.each([403, 404, 409, 422, 500])("exposes safe API errors for HTTP %s", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status, json: async () => ({ detail: "Request rejected" }) }));
    await expect(api.health()).rejects.toMatchObject({ status, message: "Request rejected" });
  });

  it("maps network failures to a retryable API error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network")));
    await expect(api.health()).rejects.toBeInstanceOf(ApiError);
  });
});
