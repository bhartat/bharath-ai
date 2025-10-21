// frontend/src/lib/api.ts (FINAL)
const API_BASE_URL = 'http://127.0.0.1:8000/api';

export class APIError extends Error {
  status: number; data: any;
  constructor(message: string, status: number, data: any) {
    super(message); this.name = 'APIError'; this.status = status; this.data = data;
  }
}

export const fetchApi = async (endpoint: string, options: RequestInit = {}) => {
  let token: string | null = null;
  if (typeof window !== "undefined") { token = localStorage.getItem('authToken'); }

  const headers = {
    'Content-Type': 'application/json', ...options.headers,
    ...(token && { 'Authorization': `Bearer ${token}` }),
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });

  if (!response.ok) {
    let errorData = { detail: `Request failed with status ${response.status}` };
    try { errorData = await response.json(); } catch (e) {}
    throw new APIError(errorData.detail, response.status, errorData);
  }

  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) { return response.json(); }
  return null;
};