// Faux backend pour tester le front. Sert /chat en SSE comme le vrai backend FastAPI.
import http from 'node:http';

const port = 8000;
const server = http.createServer((req, res) => {
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    return res.end();
  }
  if (req.url === '/chat' && req.method === 'POST') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
    });
    const tokens = ['Bonjour ', 'depuis ', 'le ', 'faux ', 'backend ', 'SSE ', '!'];
    let i = 0;
    const interval = setInterval(() => {
      if (i >= tokens.length) {
        res.write(`data: ${JSON.stringify({ type: 'done' })}\n\n`);
        clearInterval(interval);
        res.end();
        return;
      }
      res.write(`data: ${JSON.stringify({ type: 'token', content: tokens[i] })}\n\n`);
      i++;
    }, 80);
    req.on('close', () => clearInterval(interval));
    return;
  }
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end('{"status":"ok"}');
  }
  res.writeHead(404).end();
});

server.listen(port, () => console.log(`mock backend on :${port}`));
