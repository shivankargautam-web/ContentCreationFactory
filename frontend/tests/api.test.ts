import { describe, expect, it, vi } from "vitest";
import { ApiClient, ApiError, type TokenStore } from "@/lib/api";
import { formatCadence, monthGrid } from "@/lib/format";
import type { TokenPair } from "@/lib/types";

function memoryStore(initial: TokenPair | null = null): TokenStore {
  let tokens = initial;
  return { get: () => tokens, set: (t) => void (tokens = t) };
}

const json = (status: number, body: unknown) =>
  new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const pair = (a: string, r = "refresh-1"): TokenPair => ({ access_token: a, refresh_token: r, token_type: "bearer", expires_in: 1800 });

describe("ApiClient", () => {
  it("stores tokens on login and sends bearer header", async () => {
    const store = memoryStore();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(200, pair("access-1")))
      .mockResolvedValueOnce(json(200, { id: "u1", email: "a@b.co" }));
    const client = new ApiClient("http://api", store, fetchMock);
    await client.login("a@b.co", "Password1");
    expect(store.get()?.access_token).toBe("access-1");
    await client.me();
    const [url, init] = fetchMock.mock.calls[1]!;
    expect(url).toBe("http://api/api/v1/auth/me");
    expect(init.headers.Authorization).toBe("Bearer access-1");
  });

  it("uses same-origin URLs when no base URL is configured", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json(200, { items: [], total: 0, limit: 20, offset: 0 }));
    const client = new ApiClient("", memoryStore(pair("access-1")), fetchMock);
    await client.listCampaigns({ status: "scheduled" });
    expect(fetchMock.mock.calls[0]![0]).toBe(`${window.location.origin}/api/v1/campaigns?status=scheduled`);
  });

  it("refreshes once on 401 and retries the original request", async () => {
    const store = memoryStore(pair("expired"));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(401, { error: { code: "invalid_token", message: "expired" } }))
      .mockResolvedValueOnce(json(200, pair("fresh", "refresh-2")))
      .mockResolvedValueOnce(json(200, { items: [], total: 0, limit: 20, offset: 0 }));
    const client = new ApiClient("http://api", store, fetchMock);
    const page = await client.listCampaigns({ status: "scheduled" });
    expect(page.total).toBe(0);
    expect(store.get()).toEqual(pair("fresh", "refresh-2"));
    expect(fetchMock.mock.calls[2]![0]).toBe("http://api/api/v1/campaigns?status=scheduled");
    expect(fetchMock.mock.calls[2]![1].headers.Authorization).toBe("Bearer fresh");
  });

  it("clears session and notifies when refresh fails", async () => {
    const store = memoryStore(pair("expired"));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json(401, { error: { code: "invalid_token", message: "expired" } }))
      .mockResolvedValueOnce(json(401, { error: { code: "invalid_token", message: "bad refresh" } }))
      .mockResolvedValue(json(401, { error: { code: "invalid_token", message: "expired" } }));
    const client = new ApiClient("http://api", store, fetchMock);
    const onUnauthorized = vi.fn();
    client.onUnauthorized = onUnauthorized;
    await expect(client.me()).rejects.toBeInstanceOf(ApiError);
    expect(store.get()).toBeNull();
    expect(onUnauthorized).toHaveBeenCalled();
  });

  it("surfaces backend error envelope and validation details", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      json(422, {
        error: { code: "validation_error", message: "Request validation failed" },
        details: [{ loc: ["body", "instruction"], msg: "String should have at least 10 characters" }],
      }),
    );
    const client = new ApiClient("http://api", memoryStore(pair("a")), fetchMock);
    const err = await client.createCampaign({ instruction: "x", platforms: ["youtube"] }).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(422);
    expect(err.code).toBe("validation_error");
    expect(err.message).toContain("instruction");
  });

  it("returns undefined for 204", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    const client = new ApiClient("http://api", memoryStore(pair("a")), fetchMock);
    await expect(client.deleteCampaign("c1")).resolves.toBeUndefined();
    expect(fetchMock.mock.calls[0]![1].method).toBe("DELETE");
  });
});

describe("format helpers", () => {
  it("describes cadence", () => {
    expect(formatCadence(24)).toBe("Daily");
    expect(formatCadence(168)).toBe("Weekly");
    expect(formatCadence(48)).toBe("Every 2 days");
    expect(formatCadence(6)).toBe("Every 6 hours");
  });

  it("builds a sunday-first 6-week month grid", () => {
    const grid = monthGrid(new Date(2026, 10, 17));
    expect(grid).toHaveLength(42);
    expect(grid[0]!.getDay()).toBe(0);
    expect(grid.some((d) => d.getMonth() === 10 && d.getDate() === 1)).toBe(true);
  });
});
