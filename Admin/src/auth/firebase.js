import { getApp, getApps, initializeApp } from '@firebase/app';
import { getAuth, GoogleAuthProvider } from '@firebase/auth';

const config = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

export const firebaseConfigurationReady = Boolean(
  config.apiKey && !config.apiKey.startsWith('replace-')
  && config.authDomain && config.appId && !config.appId.startsWith('replace-')
  && config.projectId === 'errno-pvt-ltd',
);

const app = firebaseConfigurationReady ? (getApps().length ? getApp() : initializeApp(config)) : null;
export const firebaseAuth = app ? getAuth(app) : null;
export const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });
