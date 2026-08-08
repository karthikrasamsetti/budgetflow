import axios from "axios";

const ACCESS = "bf_access";
const REFRESH = "bf_refresh";

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS);
  },
  get refresh() {
    return localStorage.getItem(REFRESH);
  },
  set({ access_token, refresh_token }) {
    localStorage.setItem(ACCESS, access_token);
    localStorage.setItem(REFRESH, refresh_token);
  },
  clear() {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
  },
};

// In dev, VITE_API_BASE is unset and calls go to "/" (Vite proxy forwards them).
// In production (Vercel), set VITE_API_BASE to the Render backend URL.
const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE || "/" });

// Cold-start UX: Render's free tier sleeps after inactivity and takes ~30-50s to
// wake. If any request is slow, broadcast an event so the UI can show a banner.
let pending = 0;
let slowTimer = null;
const emit = (waking) => window.dispatchEvent(new CustomEvent("bf:waking", { detail: waking }));

const startTracking = () => {
  pending += 1;
  if (slowTimer === null) {
    slowTimer = setTimeout(() => emit(true), 2500);
  }
};
const stopTracking = () => {
  pending = Math.max(0, pending - 1);
  if (pending === 0) {
    clearTimeout(slowTimer);
    slowTimer = null;
    emit(false);
  }
};

api.interceptors.request.use((config) => {
  startTracking();
  const t = tokens.access;
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// On 401, try one refresh, then replay the original request.
let refreshing = null;
api.interceptors.response.use(
  (r) => {
    stopTracking();
    return r;
  },
  async (error) => {
    stopTracking();
    const original = error.config;
    if (error.response?.status === 401 && !original._retried && tokens.refresh) {
      original._retried = true;
      try {
        // Use `api` (not bare axios) so the request hits the configured backend
        // base URL in production, not the Vercel origin.
        refreshing = refreshing || api.post("/auth/refresh", { refresh_token: tokens.refresh });
        const { data } = await refreshing;
        refreshing = null;
        tokens.set(data);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch (e) {
        refreshing = null;
        tokens.clear();
        window.location.href = "/login";
        return Promise.reject(e);
      }
    }
    return Promise.reject(error);
  },
);

export default api;