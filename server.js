// Arnob Special Bank — frontend server
// Serves the static HTML/CSS/JS UI and proxies /api/* to the Python (Flask) backend,
// so the browser only ever talks to one origin.

require("dotenv").config();
const express = require("express");
const path = require("path");
const { createProxyMiddleware } = require("http-proxy-middleware");

const app = express();
const PORT = process.env.PORT || 3000;
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:5000";

// Proxy every /api request straight to the Flask backend
app.use(
  "/api",
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
  })
);

// Serve the static frontend
app.use(express.static(path.join(__dirname, "public")));

// Fallback: any unmatched route serves index.html (simple SPA-style routing not
// required here since we use plain multi-page HTML, but this keeps deep-links safe)
app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "404.html"), (err) => {
    if (err) res.status(404).send("Page not found");
  });
});

app.listen(PORT, () => {
  console.log(`Arnob Special Bank frontend running at http://localhost:${PORT}`);
  console.log(`Proxying /api requests to ${BACKEND_URL}`);
});
