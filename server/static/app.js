/* OGK App - JavaScript chung */

const OGK = {
    getToken() {
        return localStorage.getItem("ogk_token");
    },

    setToken(token) {
        localStorage.setItem("ogk_token", token);
    },

    clearToken() {
        localStorage.removeItem("ogk_token");
    },

    async fetch(url, options = {}) {
        const token = this.getToken();
        const headers = options.headers || {};
        if (token) {
            headers["Authorization"] = "Bearer " + token;
        }
        if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
            headers["Content-Type"] = "application/json";
            options.body = JSON.stringify(options.body);
        }
        options.headers = headers;
        return fetch(url, options);
    },

    formatDate(isoString) {
        if (!isoString) return "?";
        return new Date(isoString).toLocaleString("vi-VN");
    },

    escapeHtml(s) {
        if (s == null) return "";
        return String(s).replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    }
};

// Tự động logout khi token hết hạn
const origFetch = window.fetch;
window.fetch = async function(url, options = {}) {
    const resp = await origFetch(url, options);
    if (resp.status === 401 && url.includes("/api/")) {
        OGK.clearToken();
        if (window.location.pathname !== "/login") {
            window.location.href = "/login";
        }
    }
    return resp;
};
