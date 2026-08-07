// Copie instrumentée de useChat.js pour test.
// On retire la condition `if (!text.trim()) return;` au profit d'un hook testable.
// En réalité on n'a rien à modifier : on importe le fichier tel quel.
// Ce wrapper existe juste pour exposer useChat à un import dynamique.

export { useChat } from '../src/hooks/useChat.js';
