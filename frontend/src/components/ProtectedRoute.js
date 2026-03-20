import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import LoadingSpinner from './LoadingSpinner';
import VerificationPending from './VerificationPending';

const ProtectedRoute = ({ children }) => {
  const { user, isAuthenticated, loading } = useAuth();
  
  // Show spinner while checking authentication
  if (loading) {
    return <LoadingSpinner message="Checking authentication..." />;
  }
  
  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  // If authenticated but email not verified, show verification page
  if (user && !user.is_verified) {
    return <VerificationPending />;
  }
  
  // Render children if authenticated and verified
  return children;
};

export default ProtectedRoute;