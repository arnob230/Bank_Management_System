// Shared API helper — talks to the Node server, which proxies to Flask at /api/*
const API = {
  base: "/api",

  token() {
    return localStorage.getItem("asb_token");
  },

  user() {
    const raw = localStorage.getItem("asb_user");
    return raw ? JSON.parse(raw) : null;
  },

  setSession(token, user) {
    localStorage.setItem("asb_token", token);
    localStorage.setItem("asb_user", JSON.stringify(user));
  },

  clearSession() {
    localStorage.removeItem("asb_token");
    localStorage.removeItem("asb_user");
  },

  async request(path, { method = "GET", body, auth = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth) {
      const t = this.token();
      if (t) headers["Authorization"] = `Bearer ${t}`;
    }
    const res = await fetch(this.base + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    let data = {};
    try {
      data = await res.json();
    } catch (e) {
      /* empty body */
    }

    if (!res.ok) {
      if (res.status === 401 && auth) {
        this.clearSession();
        window.location.href = "/index.html";
      }
      throw new Error(data.error || "Something went wrong");
    }
    return data;
  },

  get(path) { return this.request(path); },
  post(path, body) { return this.request(path, { method: "POST", body }); },
};

// Guard for pages that require login
function requireAuth() {
  if (!API.token()) {
    window.location.href = "/index.html";
  }
}

// Guard for admin-only pages
function requireAdmin() {
  requireAuth();
  const u = API.user();
  if (!u || (u.role !== "admin" && u.role !== "teller")) {
    window.location.href = "/dashboard.html";
  }
}

function money(n) {
  const v = Number(n || 0);
  return v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function initials(name) {
  return (name || "?").split(" ").map(p => p[0]).join("").slice(0, 2).toUpperCase();
}
