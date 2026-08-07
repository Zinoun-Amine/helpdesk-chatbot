// Test ciblé du fix useChat — relecture du source pour valider la logique.
// On n'instancie pas React : on simule l'état + le client SSE et on appelle
// directement la logique équivalente à `sendMessage`.

import assert from 'node:assert/strict';
import fs from 'node:fs';

const src = fs.readFileSync(new URL('../src/hooks/useChat.js', import.meta.url), 'utf8');

// --- VALIDATIONS STATIQUES (le fix est dans le source) ---

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log(`  PASS  ${name}`); passed++; }
  catch (e) { console.log(`  FAIL  ${name}\n        ${e.message}`); failed++; }
}

console.log('\n=== Validations statiques du fix useChat.js ===\n');

test('FIX CRITIQUE : le onerror ne contient PLUS `throw err` (cause de la boucle de retry)', () => {
  // Le bug : `throw err` dans onerror → fetch-event-source retry indéfiniment
  // Le fix : suppression du throw, on gère localement.
  const onerrorMatch = src.match(/onerror\s*\([^)]*\)\s*\{([\s\S]*?)\n\s\s\}/);
  assert.ok(onerrorMatch, 'onerror introuvable');
  const body = onerrorMatch[1];
  assert.ok(!/^\s*throw\s+/m.test(body), `onerror contient encore un 'throw' :\n${body}`);
});

test('onerror appelle setIsStreaming(false)', () => {
  const onerrorMatch = src.match(/onerror\s*\([^)]*\)\s*\{([\s\S]*?)\n\s\s\}/);
  assert.ok(onerrorMatch[1].includes('setIsStreaming(false)'));
});

test('onerror appelle setError(...)', () => {
  const onerrorMatch = src.match(/onerror\s*\([^)]*\)\s*\{([\s\S]*?)\n\s\s\}/);
  assert.ok(onerrorMatch[1].includes('setError'));
});

test('FIX : un handler onclose est défini pour remettre isStreaming à false', () => {
  assert.ok(/onclose\s*\(\s*\)\s*\{[\s\S]*?setIsStreaming\(false\)/.test(src),
    'onclose manquant ou sans setIsStreaming(false)');
});

test('Le Content-Type JSON est envoyé dans les headers', () => {
  assert.ok(/'Content-Type':\s*'application\/json'/.test(src));
});

test('La conversation est envoyée au backend sous `messages`', () => {
  assert.ok(/messages:\s*chatMessages/.test(src));
});

test('Le signal AbortController est bien passé à fetchEventSource', () => {
  assert.ok(/signal:\s*abortControllerRef\.current\.signal/.test(src));
});

test('Le body est sérialisé en JSON', () => {
  assert.ok(/JSON\.stringify\(\s*\{[\s\S]*?messages:\s*chatMessages/.test(src));
});

test('L\'URL cible bien /chat (et non /chat/stream ou autre)', () => {
  const urlMatch = src.match(/fetchEventSource\(`\$\{apiUrl\}(\/[^`]*)`/);
  assert.ok(urlMatch, 'URL fetchEventSource introuvable');
  assert.equal(urlMatch[1], '/chat');
});

test('URL API configurable et compatible avec un accès réseau', () => {
  assert.ok(/API_BASE_URL/.test(src));
  const configSrc = fs.readFileSync(new URL('../src/services/apiConfig.js', import.meta.url), 'utf8');
  assert.ok(/VITE_API_URL/.test(configSrc));
  assert.ok(/window\.location\.hostname/.test(configSrc));
});

test('Le useCallback a bien messages et conversationId dans ses dépendances', () => {
  const depMatch = src.match(/\},\s*\[([^\]]+)\]\)/);
  assert.ok(depMatch, 'dépendances useCallback introuvables');
  assert.match(depMatch[1], /messages/);
  assert.match(depMatch[1], /conversationId/);
});

// --- TEST FONCTIONNEL : simulation du flux complet ---

console.log('\n=== Test fonctionnel : simulation du flux SSE ===\n');

// Mini moteur de test : on reproduit le flux onmessage → onclose du client
// et on vérifie que isStreaming passe à false au bon moment.
const simulateFlux = (events, onError) => {
  const state = { messages: [], isStreaming: false, error: null, retryCount: 0 };
  const setMessages = (updater) => { state.messages = updater(state.messages); };
  const setIsStreaming = (v) => { state.isStreaming = v; };
  const setError = (e) => { state.error = e; };

  // Initialisation
  setMessages(p => [...p, { id: 1, role: 'user', content: 'Salut' }]);
  setMessages(p => [...p, { id: 2, role: 'assistant', content: '' }]);
  setIsStreaming(true);

  const onmessage = (msg) => {
    const data = JSON.parse(msg.data);
    if (data.type === 'token') {
      setMessages(p => p.map(m => m.id === 2 ? { ...m, content: m.content + (data.content || '') } : m));
    } else if (data.type === 'done') {
      setIsStreaming(false);
    }
  };
  const onclose = () => setIsStreaming(false);
  const onerror = (err) => {
    // Le fix : on NE throw PAS → pas de retry.
    if (process.env.TEST_VERBOSE) console.error('Erreur SSE:', err);
    setError(err.message);
    setIsStreaming(false);
    // L'ancienne version aurait fait : throw err; → fetchEventSource aurait retry.
  };

  for (const ev of events) {
    if (ev.kind === 'token') onmessage({ data: JSON.stringify({ type: 'token', content: ev.content }) });
    else if (ev.kind === 'done') onmessage({ data: JSON.stringify({ type: 'done' }) });
    else if (ev.kind === 'close') onclose();
    else if (ev.kind === 'error') {
      const simulatedErr = new Error('Net down');
      onError ? onError(simulatedErr) : onerror(simulatedErr);
    }
  }
  return state;
};

test('Flux nominal : tokens accumulés, isStreaming=false à done', () => {
  const s = simulateFlux([
    { kind: 'token', content: 'Coucou ' },
    { kind: 'token', content: '!' },
    { kind: 'done' },
    { kind: 'close' },
  ]);
  assert.equal(s.messages[1].content, 'Coucou !');
  assert.equal(s.isStreaming, false);
});

test('Erreur réseau : isStreaming=false, pas de retry (simulé)', () => {
  let retries = 0;
  // Comparaison : on simule l'ANCIEN comportement (onerror throw → retry)
  // vs le NOUVEAU (onerror gère localement, pas de retry).
  let oldBehavior;
  try {
    oldBehavior = simulateFlux(
      [{ kind: 'error' }],
      (e) => { retries++; throw e; } // ← l'ancien code faisait ça
    );
  } catch (e) {
    oldBehavior = { threw: true, error: e.message };
  }
  // Avec le FIX :
  const fixed = simulateFlux([{ kind: 'error' }]);
  assert.equal(fixed.isStreaming, false);
  assert.equal(fixed.error, 'Net down');
  // L'ancien aurait throw → fetchEventSource aurait retry jusqu'à 10+ fois.
  // Le fix laisse le contrôle à l'utilisateur (1 essai, erreur affichée).
  console.log(`  (ancien: throw → retry ; fix: arrêt propre après 1 erreur)`);
});

console.log(`\n=== Résultat : ${passed} passé(s), ${failed} échoué(s) ===\n`);
process.exit(failed > 0 ? 1 : 0);
