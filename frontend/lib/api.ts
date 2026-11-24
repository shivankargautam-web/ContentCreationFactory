import type {
  AnalyticsSummary,
  CalendarEvent,
  Campaign,
  CampaignAnalytics,
  CampaignCreate,
  CampaignDetail,
  CampaignStatus,
  ContentItemDetail,
  OAuthProviders,
  Page,
  Platform,
  PlatformAccount,
  PlatformAccountCreate,
  Role,
  TimeseriesPoint,
  TokenPair,
  User,
} from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const PREFIX = "/api/v1";
const STORAGE_KEY = "acf.tokens";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface TokenStore {
  get(): TokenPair | null;
  set(tokens: TokenPair | null): void;
}

export const browserTokenStore: TokenStore = {
  get() {
    if (typeof window === "undefined") return null;
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as TokenPair) : null;
    } catch {
      return null;
    }
  },
  set(tokens) {
    if (typeof window === "undefined") return;
    if (tokens) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
    else window.localStorage.removeItem(STORAGE_KEY);
  },
};

type Query = Record<string, string | number | boolean | undefined | null>;

interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Query;
  auth?: boolean;
}

/** Thin typed client over the FastAPI contract with transparent access-token refresh. */
export class ApiClient {
  private refreshing: Promise<boolean> | null = null;
  onUnauthorized: (() => void) | null = null;

  constructor(
    private readonly baseUrl: string = API_URL,
    private readonly tokens: TokenStore = browserTokenStore,
    private readonly fetchImpl: typeof fetch = (...args) => fetch(...args),
  ) {}

  async request<T>(path: string, opts: RequestOptions = {}, retry = true): Promise<T> {
    const { method = "GET", body, query, auth = true } = opts;
    const url = new URL(`${this.baseUrl}${PREFIX}${path}`);
    for (const [k, v] of Object.entries(query ?? {})) {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
    }
    const headers: Record<string, string> = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const access = auth ? this.tokens.get()?.access_token : undefined;
    if (access) headers.Authorization = `Bearer ${access}`;

    const res = await this.fetchImpl(url.toString(), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });

    if (res.status === 401 && auth && retry && this.tokens.get()?.refresh_token) {
      if (await this.refresh()) return this.request<T>(path, opts, false);
    }
    if (res.status === 401 && auth) {
      this.tokens.set(null);
      this.onUnauthorized?.();
    }
    if (!res.ok) {
      let code = "http_error";
      let message = res.statusText || `Request failed (${res.status})`;
      let details: unknown;
      try {
        const data = await res.json();
        code = data?.error?.code ?? code;
        message = data?.error?.message ?? message;
        details = data?.details;
        if (Array.isArray(details) && details.length) {
          const first = details[0] as { loc?: unknown[]; msg?: string };
          message = `${message}: ${(first.loc ?? []).slice(1).join(".")} ${first.msg ?? ""}`.trim();
        }
      } catch {
        /* non-JSON error body */
      }
      throw new ApiError(res.status, code, message, details);
    }
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  }

  private refresh(): Promise<boolean> {
    if (!this.refreshing) {
      const refreshToken = this.tokens.get()?.refresh_token;
      this.refreshing = (async () => {
        try {
          const pair = await this.request<TokenPair>(
            "/auth/refresh",
            { method: "POST", body: { refresh_token: refreshToken }, auth: false },
            false,
          );
          this.tokens.set(pair);
          return true;
        } catch {
          this.tokens.set(null);
          return false;
        } finally {
          this.refreshing = null;
        }
      })();
    }
    return this.refreshing;
  }

  // --- auth ---
  async login(email: string, password: string): Promise<TokenPair> {
    const pair = await this.request<TokenPair>("/auth/login", { method: "POST", body: { email, password }, auth: false });
    this.tokens.set(pair);
    return pair;
  }
  register(email: string, password: string, full_name?: string) {
    return this.request<User>("/auth/register", { method: "POST", body: { email, password, full_name }, auth: false });
  }
  logout() {
    this.tokens.set(null);
  }
  hasSession() {
    return Boolean(this.tokens.get()?.access_token);
  }
  me() {
    return this.request<User>("/auth/me");
  }

  // --- users ---
  updateProfile(full_name: string | null) {
    return this.request<User>("/users/me", { method: "PATCH", body: { full_name } });
  }
  listUsers(limit = 100, offset = 0) {
    return this.request<Page<User>>("/users", { query: { limit, offset } });
  }
  setRole(userId: string, role: Role) {
    return this.request<User>(`/users/${userId}/role`, { method: "PATCH", body: { role } });
  }

  // --- campaigns ---
  createCampaign(payload: CampaignCreate) {
    return this.request<CampaignDetail>("/campaigns", { method: "POST", body: payload });
  }
  listCampaigns(params: { status?: CampaignStatus; limit?: number; offset?: number } = {}) {
    return this.request<Page<Campaign>>("/campaigns", { query: params });
  }
  getCampaign(id: string) {
    return this.request<CampaignDetail>(`/campaigns/${id}`);
  }
  setCampaignStatus(id: string, status: CampaignStatus) {
    return this.request<CampaignDetail>(`/campaigns/${id}/status`, { method: "PATCH", body: { status } });
  }
  generateCampaign(id: string) {
    return this.request<CampaignDetail>(`/campaigns/${id}/generate`, { method: "POST" });
  }
  deleteCampaign(id: string) {
    return this.request<void>(`/campaigns/${id}`, { method: "DELETE" });
  }
  calendar(start: Date, end: Date) {
    return this.request<CalendarEvent[]>("/campaigns/calendar", {
      query: { start: start.toISOString(), end: end.toISOString() },
    });
  }

  // --- content ---
  getContentItem(id: string) {
    return this.request<ContentItemDetail>(`/content-items/${id}`);
  }
  regenerateContentItem(id: string) {
    return this.request<ContentItemDetail>(`/content-items/${id}/regenerate`, { method: "POST" });
  }
  videoUrl(id: string) {
    return this.request<{ url: string }>(`/content-items/${id}/video-url`);
  }

  // --- platform accounts ---
  listAccounts() {
    return this.request<PlatformAccount[]>("/platform-accounts");
  }
  connectAccount(payload: PlatformAccountCreate) {
    return this.request<PlatformAccount>("/platform-accounts", { method: "POST", body: payload });
  }
  oauthProviders() {
    return this.request<OAuthProviders>("/platform-accounts/oauth/providers");
  }
  oauthAuthorizeUrl(platform: Platform) {
    return this.request<{ authorization_url: string }>(`/platform-accounts/oauth/${platform}/authorize`);
  }
  disconnectAccount(id: string) {
    return this.request<void>(`/platform-accounts/${id}`, { method: "DELETE" });
  }

  // --- analytics ---
  analyticsSummary() {
    return this.request<AnalyticsSummary>("/analytics/summary");
  }
  timeseries(days = 30) {
    return this.request<TimeseriesPoint[]>("/analytics/timeseries", { query: { days } });
  }
  campaignAnalytics(id: string, days = 30) {
    return this.request<CampaignAnalytics>(`/analytics/campaigns/${id}`, { query: { days } });
  }
}

export const api = new ApiClient();
