import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { onIdTokenChanged, signInWithPopup, signOut } from '@firebase/auth';
import { firebaseAuth, firebaseConfigurationReady, googleProvider } from './firebase';
import { api, ApiError } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [admin, setAdmin] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminError, setAdminError] = useState(null);
  const [authError, setAuthError] = useState('');
  const generation = useRef(0);

  const verifyAdmin = useCallback(async (currentUser) => {
    const call = ++generation.current;
    if (!currentUser) {
      setAdmin(null);
      setAdminError(null);
      setAdminLoading(false);
      return;
    }
    setAdmin(null);
    setAdminError(null);
    setAdminLoading(true);
    try {
      const result = await api.adminMe(currentUser);
      if (call === generation.current) setAdmin(result);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        await signOut(firebaseAuth);
      }
      if (call === generation.current) setAdminError(error);
    } finally {
      if (call === generation.current) setAdminLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!firebaseConfigurationReady || !firebaseAuth) {
      setAuthError('Firebase web configuration is missing. Add the VITE_FIREBASE_* settings for errno-pvt-ltd.');
      setAuthLoading(false);
      return undefined;
    }
    return onIdTokenChanged(firebaseAuth, async (nextUser) => {
    setUser(nextUser);
    setAuthLoading(false);
    if (nextUser) await verifyAdmin(nextUser);
    else await verifyAdmin(null);
  }, (error) => {
    setAuthError(error.message || 'Firebase authentication could not be restored.');
    setAuthLoading(false);
    });
  }, [verifyAdmin]);

  const signIn = useCallback(async () => {
    setAuthError('');
    if (!firebaseConfigurationReady) {
      const error = new Error('Firebase web configuration is incomplete. Set the VITE_FIREBASE_* values and use project errno-pvt-ltd.');
      setAuthError(error.message);
      throw error;
    }
    try {
      await signInWithPopup(firebaseAuth, googleProvider);
    } catch (error) {
      const message = error.code === 'auth/popup-closed-by-user'
        ? 'Sign-in was closed before it completed.'
        : error.code === 'auth/popup-blocked'
          ? 'Your browser blocked the sign-in window. Allow pop-ups and try again.'
          : error.message || 'Google sign-in failed. Please try again.';
      setAuthError(message);
      throw error;
    }
  }, []);

  const logout = useCallback(() => signOut(firebaseAuth), []);
  const retryAdminCheck = useCallback(() => user && verifyAdmin(user), [user, verifyAdmin]);

  return (
    <AuthContext.Provider value={{ user, admin, authLoading, adminLoading, adminError, authError, signIn, logout, retryAdminCheck }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
