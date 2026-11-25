const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("staff_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// --- Types ---

export interface TokenCreateResponse {
  token_id: number;
  token_number: string;
  service_category: string;
  status: string;
  registration_time: string;
  estimated_wait_time: number | null;
  queue_url: string;
}

export interface PublicDisplayResponse {
  now_serving: { counter_id: number; counter_name: string; token_number: string | null }[];
  upcoming: string[];
  recently_completed: string[];
}

export interface OverviewResponse {
  total_registered_today: number;
  currently_waiting: number;
  being_served: number;
  completed_today: number;
  active_counters: number;
  counters_now_serving: Record<string, string | null>;
}

export interface TokenStaffRow {
  token_id: number;
  token_number: string;
  phone_masked: string;
  service_category: string;
  status: string;
  registration_time: string;
  called_time: string | null;
  counter_id: number | null;
  estimated_wait_time: number | null;
}

export interface CounterResponse {
  counter_id: number;
  counter_name: string;
  assigned_service: string | null;
  current_token_id: number | null;
  current_token_number: string | null;
  counter_status: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
  username: string;
}

// --- Kiosk ---

export const getServices = () => request<string[]>("/api/services");

export const createToken = (phone_number: string, service_category: string) =>
  request<TokenCreateResponse>("/api/kiosk/tokens", {
    method: "POST",
    body: JSON.stringify({ phone_number, service_category }),
  });

// --- Public display ---

export const getPublicDisplay = () => request<PublicDisplayResponse>("/api/public/display");

// --- Auth ---

export const login = (username: string, password: string) =>
  request<LoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });

// --- Staff ---

export const getOverview = () => request<OverviewResponse>("/api/staff/overview");

export const listTokens = (params: { status?: string; service?: string; q?: string } = {}) => {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.service) qs.set("service", params.service);
  if (params.q) qs.set("q", params.q);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<TokenStaffRow[]>(`/api/staff/tokens${suffix}`);
};

export const markAbsent = (tokenId: number) =>
  request<TokenStaffRow>(`/api/staff/tokens/${tokenId}/absent`, { method: "POST" });

export const requeueToken = (tokenId: number) =>
  request<TokenStaffRow>(`/api/staff/tokens/${tokenId}/requeue`, { method: "POST" });

// --- Counters ---

export const listCounters = () => request<CounterResponse[]>("/api/counters");

export const callNext = (counterId: number) =>
  request<{ token_id: number; token_number: string; service_category: string; counter_name: string }>(
    `/api/counters/${counterId}/call-next`,
    { method: "POST" },
  );

export const recallToken = (counterId: number, tokenId: number) =>
  request<{ token_id: number; status: string }>(`/api/counters/${counterId}/recall/${tokenId}`, { method: "POST" });

export const markServing = (counterId: number, tokenId: number) =>
  request<{ token_id: number; status: string }>(`/api/counters/${counterId}/serving/${tokenId}`, { method: "POST" });

export const completeToken = (counterId: number, tokenId: number) =>
  request<{ token_id: number; status: string }>(`/api/counters/${counterId}/complete/${tokenId}`, {
    method: "POST",
  });

export const skipToken = (counterId: number, tokenId: number) =>
  request<{ token_id: number; status: string }>(`/api/counters/${counterId}/skip/${tokenId}`, { method: "POST" });
