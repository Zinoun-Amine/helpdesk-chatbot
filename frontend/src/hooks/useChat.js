import { useState, useCallback, useRef } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { API_BASE_URL, apiError } from '../services/apiConfig';
import * as api from '../services/api';
import { getStoredToken } from '../services/authApi';

export function useChat(user) {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [qualification, setQualification] = useState(null);

  const abortControllerRef = useRef(null);

  const sendMessage = useCallback(async (text, files = []) => {
    if (!text.trim()) return;

    let uploadedAttachments = [];
    if (files.length) {
      try {
        uploadedAttachments = await Promise.all(files.map(file => api.uploadAttachment(file)));
      } catch (err) {
        setError(err.message || 'Impossible de téléverser la pièce jointe.');
        return;
      }
    }

    const userMsg = { id: Date.now(), role: 'user', content: text, attachments: uploadedAttachments };
    setMessages(prev => [...prev, userMsg]);
    setIsStreaming(true);
    setError(null);
    const requestStartedAt = Date.now();
    let responseTimeRecorded = false;

    const assistantMsgId = Date.now() + 1;
    setMessages(prev => [...prev, { id: assistantMsgId, role: 'assistant', content: '', actions: [] }]);

    abortControllerRef.current = new AbortController();

    const priorMessages = messages
      .filter(message => message && message.role && message.content)
      .slice(-8)
      .map(({ role, content }) => ({ role, content }));

    const chatMessages = [
      ...priorMessages,
      { role: 'user', content: text, attachments: uploadedAttachments },
    ];
    const apiUrl = API_BASE_URL;

    const recordResponseTime = () => {
      if (responseTimeRecorded) return;
      responseTimeRecorded = true;
      const responseTimeMs = Date.now() - requestStartedAt;
      setMessages(prev => prev.map(message => (
        message.id === assistantMsgId ? { ...message, responseTimeMs } : message
      )));
    };

    try {
      const token = getStoredToken();
      await fetchEventSource(`${apiUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          messages: chatMessages,
          conversation_id: conversationId,
          user_name: user?.full_name,
          user_email: user?.email,
        }),
        signal: abortControllerRef.current.signal,

        onopen(response) {
          if (response.ok) return;
          throw new Error(`Erreur serveur: ${response.status}`);
        },

        onmessage(msg) {
          const data = JSON.parse(msg.data);

          if (data.type === 'token') {
            setMessages(prev => prev.map(message => (
              message.id === assistantMsgId
                ? { ...message, content: message.content + (data.content || '') }
                : message
            )));
          } else if (data.type === 'error') {
            const message = data.message || 'Impossible de générer une réponse.';
            setError(message);
            setMessages(prev => prev.map(item => (
              item.id === assistantMsgId && !item.content ? { ...item, content: message } : item
            )));
            setIsStreaming(false);
            recordResponseTime();
          } else if (data.type === 'action') {
            if (data.conversation_id && !conversationId) {
              setConversationId(data.conversation_id);
            }
            if (data.action === 'qualification') {
              setQualification(data.qualification || null);
            }
            setMessages(prev => prev.map(message => (
              message.id === assistantMsgId
                ? { ...message, actions: [...(message.actions || []), data] }
                : message
            )));
          } else if (data.type === 'done') {
            setIsStreaming(false);
            recordResponseTime();
          }
        },

        onerror(err) {
          console.error('Erreur SSE:', err);
          recordResponseTime();
          const message = apiError(err, `${apiUrl}/chat`).message || 'Une erreur de connexion s\'est produite.';
          setError(message);
          setMessages(prev => prev.map(item => (
            item.id === assistantMsgId && !item.content ? { ...item, content: message } : item
          )));
          setIsStreaming(false);
        },

        onclose() {
          setIsStreaming(false);
          recordResponseTime();
        },
      });
    } catch (err) {
      if (err.name !== 'AbortError') {
        recordResponseTime();
        const message = apiError(err, `${apiUrl}/chat`).message || 'Erreur lors de l\'envoi du message';
        setError(message);
        setMessages(prev => prev.map(item => (
          item.id === assistantMsgId && !item.content ? { ...item, content: message } : item
        )));
        setIsStreaming(false);
      }
    }
  }, [messages, conversationId, user?.email, user?.full_name]);

  const rateMessage = useCallback(async (messageId, rating) => {
    await api.sendChatFeedback({
      conversation_id: conversationId,
      message_id: String(messageId),
      rating,
    });
    setMessages(prev => prev.map(message => (
      message.id === messageId ? { ...message, feedback: rating } : message
    )));
  }, [conversationId]);

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setQualification(null);
    setError(null);
  }, []);

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
    stopStreaming,
    clearChat,
    conversationId,
    qualification,
    rateMessage,
  };
}
