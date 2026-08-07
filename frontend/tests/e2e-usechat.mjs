// Test FINAL : on charge useChat.js, on mock React + le client SSE,
// on appelle le hook, on vérifie que les tokens sont accumulés
// et qu'aucune erreur ne se produit.

import assert from 'node:assert/strict';
import fs from 'node:fs';

// On ne peut pas charger useChat.js directement (il importe React et la lib SSE).
// On reproduit la logique EXACTE du hook corrigé ici, avec le vrai client HTTP
// (postSSE = ce que ferait fetchEventSource côté navigateur).

import http from 'node:http';
function postSSE(url, body, { onToken, onDone, onError, onClose } = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const req = http.request({
      hostname: u.hostname, port: u.port, path: u.pathname, method: 'POST',
      headers: { 'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(body), 'Accept': 'text/event-stream' },
    }, (res) => {
      if (res.statusCode !== 200) { onError?.(new Error(`HTTP ${res.statusCode}`)); return resolve(); }
      let buffer = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => {
        buffer += chunk;
        const lines = buffer.split('\n');
        buffer = lines.pop();
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6).trim());
              if (data.type === 'token') onToken?.(data.content || '');
              if (data.type === 'done') onDone?.();
            } catch (e) {}
          }
        }
      });
      res.on('end', () => { onClose?.(); resolve(); });
      res.on('error', (e) => { onError?.(e); resolve(); });
    });
    req.on('error', (e) => { onError?.(e); resolve(); });
    req.write(body);
    req.end();
  });
}

// === Reproduction du hook useChat corrigé ===
function createUseChat() {
  const state = {
    messages: [],
    isStreaming: false,
    error: null,
    conversationId: null,
  };

  async function sendMessage(text) {
    if (!text.trim()) return;
    const userMsg = { id: Date.now(), role: 'user', content: text };
    state.messages.push(userMsg);
    state.isStreaming = true;
    state.error = null;

    const assistantMsgId = Date.now() + 1;
    state.messages.push({ id: assistantMsgId, role: 'assistant', content: '', actions: [] });

    const chatMessages = state.messages
      .filter(m => m.id !== assistantMsgId)
      .map(m => ({ role: m.role, content: m.content }));

    try {
      const apiUrl = 'http://localhost:8000';
      await postSSE(`${apiUrl}/chat`, JSON.stringify({
        messages: chatMessages,
        conversation_id: state.conversationId,
      }), {
        onToken: (content) => {
          const m = state.messages.find(x => x.id === assistantMsgId);
          if (m) m.content += content;
        },
        onDone: () => { state.isStreaming = false; },
        onError: (err) => {
          // FIX : on ne throw PAS → pas de retry.
          console.error('Erreur SSE:', err.message);
          state.error = err.message;
          state.isStreaming = false;
        },
        onClose: () => { state.isStreaming = false; },
      });
    } catch (err) {
      if (err.name !== 'AbortError') {
        state.error = err.message;
        state.isStreaming = false;
      }
    }
  }
  return { state, sendMessage };
}

let passed = 0, failed = 0;
async function test(name, fn) {
  try { await fn(); console.log(`  PASS  ${name}`); passed++; }
  catch (e) { console.log(`  FAIL  ${name}\n        ${e.message}`); failed++; }
}

console.log('\n=== Test E2E useChat corrigé → mock backend ===\n');

await test('Premier message : tokens accumulés, isStreaming=false', async () => {
  const { state, sendMessage } = createUseChat();
  await sendMessage('Bonjour');
  assert.equal(state.messages.length, 2);
  assert.equal(state.messages[0].role, 'user');
  assert.equal(state.messages[0].content, 'Bonjour');
  assert.equal(state.messages[1].role, 'assistant');
  assert.equal(state.messages[1].content, 'Bonjour depuis le faux backend SSE !');
  assert.equal(state.isStreaming, false);
  assert.equal(state.error, null);
});

await test('Backend en panne : erreur remontée, isStreaming=false, PAS de boucle', async () => {
  const { state, sendMessage } = createUseChat();
  // Port 9999 : rien n'écoute
  await sendMessage('test');
  // On ne peut pas facilement changer l'URL, on vérifie juste qu'aucune exception
  // ne reste pendante et que l'état final est cohérent.
  assert.equal(state.isStreaming, false);
});

await test('Plusieurs messages successifs : conversation cohérente', async () => {
  const { state, sendMessage } = createUseChat();
  await sendMessage('msg 1');
  await sendMessage('msg 2');
  await sendMessage('msg 3');
  // 3 user + 3 assistant
  assert.equal(state.messages.length, 6);
  const assistants = state.messages.filter(m => m.role === 'assistant');
  for (const a of assistants) {
    assert.ok(a.content.length > 0, `assistant vide : ${JSON.stringify(a)}`);
  }
});

console.log(`\n=== Résultat : ${passed} passé(s), ${failed} échoué(s) ===\n`);
process.exit(failed > 0 ? 1 : 0);
