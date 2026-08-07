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

const api = axios.create({ baseURL: "/" });

api.interceptors.request.use((config) => {
  const t = tokens.access;
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// On 401, try one refresh, then replay the original request.
let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retried && tokens.refresh) {
      original._retried = true;
      try {
        refreshing =
          refreshing ||
          axios.post("/auth/refresh", { refresh_token: tokens.refresh });
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
