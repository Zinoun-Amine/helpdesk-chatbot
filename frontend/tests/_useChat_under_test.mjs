import { useState, useCallback, useRef } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  
  const abortControllerRef = useRef(null);

  const sendMessage = useCallback(async (text) => {
    if (!text.trim()) return;

    // Ajouter le message utilisateur
    const userMsg = { id: Date.now(), role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setIsStreaming(true);
    setError(null);

    // Initialiser le message assistant vide
    const assistantMsgId = Date.now() + 1;
    setMessages(prev => [...prev, { id: assistantMsgId, role: 'assistant', content: '', actions: [] }]);

    abortControllerRef.current = new AbortController();

    // Utiliser le snapshot déjà mis à jour de `messages` (incluant le user message)
    // pour éviter les problèmes de closure et la duplication.
    const baseHistory = messages.map(message => ({ role: message.role, content: message.content }));
    const chatMessages = [...baseHistory, { role: 'user', content: text }];

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      await fetchEventSource(`${apiUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: chatMessages,
          conversation_id: conversationId,
        }),
        signal: abortControllerRef.current.signal,

        onopen(response) {
          if (response.ok) return;
          throw new Error(`Erreur serveur: ${response.status}`);
        },

        onmessage(msg) {
          const data = JSON.parse(msg.data);

          if (data.type === 'token') {
            setMessages(prev => prev.map(m => {
              if (m.id === assistantMsgId) {
                return { ...m, content: m.content + (data.content || '') };
              }
              return m;
            }));
          }
          else if (data.type === 'action') {
            if (data.conversation_id && !conversationId) {
              setConversationId(data.conversation_id);
            }
            setMessages(prev => prev.map(m => {
              if (m.id === assistantMsgId) {
                return { ...m, actions: [...(m.actions || []), data] };
              }
              return m;
            }));
          }
          else if (data.type === 'done') {
            setIsStreaming(false);
          }
        },

        onerror(err) {
          // Important : ne PAS relancer l'erreur ici.
          // fetch-event-source interpréterait un `throw` comme une demande
          // de reconnexion automatique (jusqu'à 10+ tentatives), ce qui bloque
          // la réponse et fige l'UI sur "Le chatbot répond...".
          console.error("Erreur SSE:", err);
          setError(err.message || "Une erreur de connexion s'est produite.");
          setIsStreaming(false);
        },

        onclose() {
          setIsStreaming(false);
        }
      });
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || "Erreur lors de l'envoi du message");
        setIsStreaming(false);
      }
    }
  }, [messages, conversationId]);

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  }, []);

  return { 
    messages, 
    isStreaming, 
    error, 
    sendMessage, 
    stopStreaming, 
    clearChat 
  };
}
