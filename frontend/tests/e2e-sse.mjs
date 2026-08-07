// Test E2E direct : on simule EXACTEMENT ce que fait fetchEventSource
// (POST + parsing SSE), et on appelle le mock backend.

import http from 'node:http';
import assert from 'node:assert/strict';

function postSSE(url, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const req = http.request({
      hostname: u.hostname,
      port: u.port,
      path: u.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body),
        'Accept': 'text/event-stream',
      },
    }, (res) => {
      if (res.statusCode !== 200) {
        return reject(new Error(`HTTP ${res.statusCode}`));
      }
      const tokens = [];
      let done = false;
      let buffer = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        buffer += chunk;
        const lines = buffer.split('\n');
        buffer = lines.pop(); // garder le chunk partiel
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6).trim());
              if (data.type === 'token') tokens.push(data.content);
              if (data.type === 'done') done = true;
            } catch (e) {}
          }
        }
      });
      res.on('end', () => resolve({ tokens, done, full: tokens.join('') }));
      res.on('error', reject);
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

let passed = 0, failed = 0;
async function test(name, fn) {
  try { await fn(); console.log(`  PASS  ${name}`); passed++; }
  catch (e) { console.log(`  FAIL  ${name}\n        ${e.message}`); failed++; }
}

console.log('\n=== Test E2E : client SSE → mock backend ===\n');

await test('POST /chat reçoit les 7 tokens + done', async () => {
  const r = await postSSE('http://localhost:8000/chat',
    JSON.stringify({ messages: [{ role: 'user', content: 'salut' }] }));
  assert.equal(r.done, true);
  assert.equal(r.full, 'Bonjour depuis le faux backend SSE !');
  console.log(`        message reçu : "${r.full}"`);
});

await test('Le Content-Type JSON est requis par le backend (ici accepté)', async () => {
  const r = await postSSE('http://localhost:8000/chat',
    JSON.stringify({ messages: [{ role: 'user', content: 'a' }] }));
  assert.ok(r.tokens.length > 0);
});

await test('Plusieurs requêtes séquentielles fonctionnent (pas de bug de ré-init)', async () => {
  for (let i = 0; i < 3; i++) {
    const r = await postSSE('http://localhost:8000/chat',
      JSON.stringify({ messages: [{ role: 'user', content: `msg ${i}` }] }));
    assert.equal(r.done, true, `tour ${i}: done manquant`);
  }
});

console.log(`\n=== Résultat E2E : ${passed} passé(s), ${failed} échoué(s) ===\n`);
process.exit(failed > 0 ? 1 : 0);
