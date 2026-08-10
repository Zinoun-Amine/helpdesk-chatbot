import { API_BASE_URL, apiError } from './apiConfig';

async function requestJSON(url, options = {}) {
  let res;
  try {
    res = await fetch(url, options);
  } catch (error) {
    throw apiError(error, url);
  }
  if (!res.ok) {
    const message = await res.text().catch(() => '');
    throw new Error(message || `HTTP ${res.status} — ${url}`);
  }
  return res.json();
}

/**
 * Rcuprer la liste des tickets rcents
 */
export async function getTickets() {
  return requestJSON(`${API_BASE_URL}/tickets`);
}

export async function searchTickets(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, value);
    }
  });
  return requestJSON(`${API_BASE_URL}/tickets?${query.toString()}`);
}

export async function getTicket(id) {
  return requestJSON(`${API_BASE_URL}/tickets/${id}`);
}

export async function getTechnicians() {
  return requestJSON(`${API_BASE_URL}/technicians`);
}

export async function assignTicket(id, payload) {
  return requestJSON(`${API_BASE_URL}/tickets/${id}/assign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

/**
 * Obtenir l'tat d'un ticket spcifique
 */
export async function getTicketStatus(id) {
  return requestJSON(`${API_BASE_URL}/tickets/${id}/status`);
}

/**
 * Mettre  jour les dtails d'un ticket
 */
export async function updateTicket(id, data) {
  return requestJSON(`${API_BASE_URL}/tickets/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
}

export async function createTicket(data) {
  return requestJSON(`${API_BASE_URL}/tickets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
}

export async function getTicketMessages(id) {
  return requestJSON(`${API_BASE_URL}/tickets/${id}/messages`);
}

export async function addTicketMessage(id, data) {
  return requestJSON(`${API_BASE_URL}/tickets/${id}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
}

export async function getTicketHistory(id) {
  return requestJSON(`${API_BASE_URL}/tickets/${id}/history`);
}

export async function draftTicketFromConversation(payload) {
  return requestJSON(`${API_BASE_URL}/tickets/from-conversation/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

export async function getDashboard(period = '30d', start = null, end = null) {
  const query = new URLSearchParams({ period });
  if (start) query.set('start', start);
  if (end) query.set('end', end);
  return requestJSON(`${API_BASE_URL}/dashboard?${query.toString()}`);
}

export async function getSettings() {
  return requestJSON(`${API_BASE_URL}/settings`);
}

export async function saveSettings(payload) {
  return requestJSON(`${API_BASE_URL}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}

export async function testProviderConnection(provider) {
  return requestJSON(`${API_BASE_URL}/settings/providers/${provider}/test`, {
    method: 'POST'
  });
}

/**
 * Mettre  jour un brouillon d'email
 */
export async function updateEmailDraft(id, data) {
  return requestJSON(`${API_BASE_URL}/email-drafts/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
}

/**
 * Envoyer un brouillon d'email
 */
export async function sendEmailDraft(id) {
  return requestJSON(`${API_BASE_URL}/email-drafts/${id}/send`, {
    method: 'POST'
  });
}

/**
 * Rechercher dans la base de connaissances
 */
export async function searchKnowledgeBase(query, topK = 3) {
  return requestJSON(`${API_BASE_URL}/kb/search?q=${encodeURIComponent(query)}&top_k=${topK}`);
}

export async function uploadAttachment(file) {
  const formData = new FormData();
  formData.append('file', file);
  return requestJSON(`${API_BASE_URL}/chat/attachments`, {
    method: 'POST',
    body: formData,
  });
}

export async function getConversations(limit = 50) {
  return requestJSON(`${API_BASE_URL}/conversations?limit=${limit}`);
}

export async function getConversation(id) {
  return requestJSON(`${API_BASE_URL}/conversations/${id}`);
}

export async function sendChatFeedback(payload) {
  return requestJSON(`${API_BASE_URL}/chat/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
