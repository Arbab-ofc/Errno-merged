import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { StatePanel } from '../components/StatePanel';

export function RequireAdmin({ children }) {
  const { user, admin, authLoading, adminLoading, adminError, retryAdminCheck, logout } = useAuth();
  const location = useLocation();

  if (authLoading) return <StatePanel title="Restoring session" detail="Checking your Firebase session…" loading />;
  if (!user) return <Navigate to="/admin/login" replace state={{ from: location }} />;
  if (adminLoading) return <StatePanel title="Checking access" detail="Verifying administrator permissions with ERRNO…" loading />;
  if (adminError?.status === 403) {
    return <StatePanel title="Administrator access required" detail="Your Firebase account is signed in, but no active ERRNO administrator permission is assigned. Contact an authorized operator." actionLabel="Sign out" onAction={logout} tone="denied" />;
  }
  if (adminError) {
    return <StatePanel title="Could not verify access" detail={adminError.message} actionLabel="Retry" onAction={retryAdminCheck} />;
  }
  if (!admin?.active) return <StatePanel title="Checking access" detail="Waiting for server authorization…" loading />;
  return children;
}
