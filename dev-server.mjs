// Local dev: serves web/ and mounts api/log.js the way Vercel does.
//   npm run dev   (in-memory storage, password "dev")   -> http://localhost:8000
import http from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import handler from "./api/log.js";

const PORT = Number(process.env.PORT || 8000);
const ROOT = new URL("./web/", import.meta.url).pathname;
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css", ".svg": "image/svg+xml", ".json": "application/json", ".webmanifest": "application/manifest+json" };

http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  if (url.pathname === "/api/log") return handler(req, res);
  let path = normalize(url.pathname === "/" ? "/index.html" : url.pathname);
  try {
    const body = await readFile(join(ROOT, path));
    res.writeHead(200, { "content-type": TYPES[extname(path)] || "application/octet-stream", "cache-control": "no-store" });
    res.end(body);
  } catch { res.writeHead(404); res.end("not found"); }
}).listen(PORT, "127.0.0.1", () => console.log(`food tracker dev server on http://localhost:${PORT}`));
