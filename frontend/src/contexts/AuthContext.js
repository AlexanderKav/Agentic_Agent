import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';
import { login as apiLogin, register as apiRegister, getCurrentUser } from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }

    // Listen for verification success event
    const handleVerification = () => {
      fetchUser();
    };

    window.addEventListener('user-verified', handleVerification);
    
    return () => {
      window.removeEventListener('user-verified', handleVerification);
    };
  }, []);

  const fetchUser = async () => {
    try {
      const userData = await getCurrentUser();
      setUser(userData);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      // If token exists but fetch fails, try unverified endpoint
      if (localStorage.getItem('token')) {
        try {
          const unverifiedData = await axios.get('http://localhost:8000/api/v1/auth/me/unverified');
          setUser(unverifiedData.data);
        } catch (e) {
          logout();
        }
      } else {
        logout();
      }
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    const data = await apiLogin(username, password);
    const { access_token, user } = data;
    
    localStorage.setItem('token', access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    setUser(user);
    
    return user;
  };

  const register = async (userData) => {
    const data = await apiRegister(userData);
    return data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  // Manual set user function (for verification)
  const setVerifiedUser = (userData) => {
    setUser(userData);
  };

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    setVerifiedUser,
    isAuthenticated: !!user
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};