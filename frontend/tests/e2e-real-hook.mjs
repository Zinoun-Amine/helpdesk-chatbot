// Test E2E FINAL : on crée un .cjs avec mocks intégrés, on require le hook
// converti en CommonJS, et on appelle useChat().

import { register } from 'node:module';
import { pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';

// === 1. Mocks globaux ===
const reactStore = new Map();
let reactCounter = 0;
const React = {
  useState(initial) {
    const id = reactCounter++;
    if (!reactStore.has(id)) {
      reactStore.set(id, { value: typeof initial === 'function' ? initial() : initial });
    }
    const entry = reactStore.get(id);
    return [entry.value, (updater) => {
      entry.value = typeof updater === 'function' ? updater(entry.value) : updater;
    }];
  },
  useRef(initial) { return { current: initial }; },
  useCallback(fn) { return fn; },
  useEffect() {},
};

function realFetchEventSource(url, options = {}) {
  return new Promise((resolve) => {
    let body = options.body || '{}';
    if (typeof body !== 'string') body = JSON.stringify(body);
    const u = new URL(url);
    const req = http.request({
      hostname: u.hostname, port: u.port, path: u.pathname, method: options.method || 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body),
        'Accept': 'text/event-stream' },
    }, (res) => {
      if (options.onopen) options.onopen({ ok: res.statusCode === 200, status: res.statusCode });
      if (res.statusCode !== 200) {
        if (options.onerror) options.onerror(new Error(`HTTP ${res.statusCode}`));
        return resolve();
      }
      let buffer = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        buffer += chunk;
        const lines = buffer.split('\n');
        buffer = lines.pop();
        for (const line of lines) {
          if (line.startsWith('data: ') && options.onmessage) {
            options.onmessage({ data: line.slice(6).trim() });
          }
        }
      });
      res.on('end', () => { if (options.onclose) options.onclose(); resolve(); });
      res.on('error', (e) => { if (options.onerror) options.onerror(e); resolve(); });
    });
    if (options.signal) options.signal.addEventListener?.('abort', () => req.destroy());
    req.on('error', (e) => { if (options.onerror) options.onerror(e); resolve(); });
    req.write(body);
    req.end();
  });
}

// === 2. Conversion du hook en CommonJS avec mocks inline ===
const hookSrc = fs.readFileSync(path.resolve('src/hooks/useChat.js'), 'utf8');
// On retire les imports ESM et on injecte les mocks
const cjsSrc = `
// Mocks CommonJS
const useState = (...a) => globalThis.__React.useState(...a);
const useRef = (...a) => globalThis.__React.useRef(...a);
const useCallback = (...a) => globalThis.__React.useCallback(...a);
const useEffect = (...a) => globalThis.__React.useEffect(...a);
const fetchEventSource = (...a) => globalThis.__FES(...a);
// Mock import.meta.env (Vite-style)
globalThis.import = globalThis.import || {};
const import_meta = { env: { VITE_API_URL: process.env.VITE_API_URL || 'http://localhost:8000' } };

${hookSrc
  .replace(/^import\s+.*?from\s+['"]react['"];?$/gm, '')
  .replace(/^import\s+.*?from\s+['"]@microsoft\/fetch-event-source['"];?$/gm, '')
  .replace(/import\.meta\.env/g, 'import_meta.env')
  .replace(/export\s+function\s+useChat/, 'function useChat')
  .replace(/^export\s*\{[^}]*\};?$/gm, '')}
module.exports = { useChat };
`;
const cjsPath = path.resolve('tests/_useChat.cjs');
fs.writeFileSync(cjsPath, cjsSrc);

globalThis.__React = React;
globalThis.__FES = realFetchEventSource;
const { useChat } = await import('node:module').then(m => m.createRequire(import.meta.url)('node:fs')); // no-op
const { createRequire } = await import('node:module');
const require = createRequire(import.meta.url);
const { useChat: hookFn } = require(cjsPath);

// === 3. Tests ===
let passed = 0, failed = 0;
async function test(name, fn) {
  try { await fn(); console.log(`  PASS  ${name}`); passed++; }
  catch (e) { console.log(`  FAIL  ${name}\n        ${e.message}\n        ${e.stack}`); failed++; }
}

console.log('\n=== Test E2E : VRAI useChat.js corrigé (en CJS) → mock backend :8000 ===\n');

await test('Hook exporté', () => {
  assert.equal(typeof hookFn, 'function');
});

await test('API de base', () => {
  reactStore.clear(); reactCounter = 0;
  const api = hookFn();
  assert.ok(Array.isArray(api.messages));
  assert.equal(typeof api.isStreaming, 'boolean');
  assert.equal(typeof api.sendMessage, 'function');
});

await test('Flux nominal : tokens accumulés via le vrai hook', async () => {
  reactStore.clear(); reactCounter = 0;
  const { messages, isStreaming, sendMessage } = hookFn();
  await sendMessage('Bonjour');
  const assistant = messages.find(m => m.role === 'assistant');
  assert.ok(assistant, 'pas de message assistant');
  assert.equal(assistant.content, 'Bonjour depuis le faux backend SSE !');
  assert.equal(isStreaming, false, `isStreaming devrait être false, vaut ${isStreaming}`);
});

await test('Erreur réseau : onerror appelé 1x, isStreaming=false', async () => {
  reactStore.clear(); reactCounter = 0;
  const origFes = globalThis.__FES;
  let errorCalls = 0;
  globalThis.__FES = (url, opts) => {
    return origFes(url.replace(':8000', ':9999'), {
      ...opts,
      onerror: (e) => { errorCalls++; if (opts?.onerror) opts.onerror(e); },
    });
  };
  try {
    const { isStreaming, sendMessage, error } = hookFn();
    await sendMessage('test');
    assert.equal(isStreaming, false, `isStreaming=${isStreaming}, devrait être false`);
    assert.equal(errorCalls, 1, `onerror appelé ${errorCalls} fois (devrait être 1)`);
    console.log(`        (erreur affichée à l'UI : "${error}")`);
  } finally {
    globalThis.__FES = origFes;
  }
});

await test('3 messages successifs : 3 assistants avec contenu', async () => {
  reactStore.clear(); reactCounter = 0;
  const { messages, sendMessage } = hookFn();
  await sendMessage('a');
  await sendMessage('b');
  await sendMessage('c');
  const assistants = messages.filter(m => m.role === 'assistant');
  assert.equal(assistants.length, 3);
  for (const a of assistants) assert.ok(a.content.length > 0, `vide : ${JSON.stringify(a)}`);
});

// Cleanup
try { fs.unlinkSync(cjsPath); } catch {}

console.log(`\n=== Résultat : ${passed} passé(s), ${failed} échoué(s) ===\n`);
process.exit(failed > 0 ? 1 : 0);
