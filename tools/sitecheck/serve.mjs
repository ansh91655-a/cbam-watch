// 만든 사이트 폴더를 이 컴퓨터 안에서만 보이는 주소로 띄운다(검사하는 동안에만).
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, resolve, sep } from "node:path";

const TYPES = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp",
  ".woff2": "font/woff2", ".xml": "application/xml; charset=utf-8", ".txt": "text/plain; charset=utf-8", ".pdf": "application/pdf", ".ico": "image/x-icon",
};

// { url: 사이트 주소(끝에 / 가 붙는다), close(): 닫기 }
export async function serve(folder) {
  const root = resolve(folder);
  const server = createServer(async (request, response) => {
    try {
      const path = decodeURIComponent(new URL(request.url, "http://x").pathname);
      const file = resolve(root, "." + (path.endsWith("/") ? path + "index.html" : path));
      if (file !== root && !file.startsWith(root + sep)) throw new Error("폴더 밖");
      const body = await readFile(file);
      response.writeHead(200, { "Content-Type": TYPES[extname(file).toLowerCase()] || "application/octet-stream", "Cache-Control": "no-store" });
      response.end(body);
    } catch (error) {
      response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("없음");
    }
  });
  await new Promise((done) => server.listen(0, "127.0.0.1", done));
  return { url: `http://127.0.0.1:${server.address().port}/`, close: () => new Promise((done) => server.close(done)) };
}
