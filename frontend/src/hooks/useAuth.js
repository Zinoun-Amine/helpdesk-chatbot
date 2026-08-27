import { useAuthContext } from '../contexts/AuthContext.jsx';

export function useAuth() {
  return useAuthContext();
}
