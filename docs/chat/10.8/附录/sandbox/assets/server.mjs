// M1 占位「游戏」服务：验证沙盒内 Node 后端可被沙盒内浏览器访问。
// 真实游戏工程由 packages/game-template 提供，这里只做链路验证。
import { createServer } from "node:http";

const PORT = Number(process.env.PORT || 3000);

const html = `<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <title>M1 Placeholder Game</title>
  <style>
    html,body{margin:0;height:100%}
    body{background:#0b0f14;color:#31d158;font-family:ui-monospace,Menlo,monospace;
         display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px}
    canvas{background:#111a22;border-radius:12px}
    #meta{opacity:.8;font-size:13px}
  </style>
</head>
<body>
  <canvas id="c" width="420" height="240"></canvas>
  <div id="meta">connecting…</div>
  <script>
    const cv = document.getElementById('c');
    const ctx = cv.getContext('2d');
    let x = 40, vx = 3, tick = 0, ping = {};
    fetch('/api/ping').then(r => r.json()).then(d => {
      ping = d;
      setInterval(loop, 16);
    });
    function loop() {
      if (x < 20 || x > cv.width - 20) vx = -vx;
      x += vx; tick++;
      ctx.fillStyle = '#111a22'; ctx.fillRect(0, 0, cv.width, cv.height);
      ctx.fillStyle = '#31d158'; ctx.beginPath();
      ctx.arc(x, cv.height / 2, 18, 0, Math.PI * 2); ctx.fill();
      document.getElementById('meta').textContent =
        'tick ' + tick + ' · pid ' + ping.pid + ' · ' + new Date(ping.ts).toLocaleTimeString();
    }
  </script>
</body>
</html>`;

const server = createServer((req, res) => {
  if (req.url && req.url.startsWith("/api/ping")) {
    res.writeHead(200, { "content-type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ ok: true, pid: process.pid, ts: Date.now() }));
    return;
  }
  res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
  res.end(html);
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`placeholder game listening on http://0.0.0.0:${PORT}`);
});
