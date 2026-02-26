import React, { createContext, useState, useContext, useEffect } from 'react';
import { authAPI } from '../services/api';
import toast from 'react-hot-toast';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await authAPI.getCurrentUser();
      setUser(response.data);
      localStorage.setItem('user', JSON.stringify(response.data));
    } catch (error) {
      console.error('Failed to fetch user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      console.log('[Auth] Logging in:', email);
      const response = await authAPI.login(email, password);
      console.log('[Auth] Login response:', response.data);
      const { access_token } = response.data;

      localStorage.setItem('token', access_token);
      setToken(access_token);

      await fetchUser();

      toast.success('Logged in successfully!');
      return { success: true };
    } catch (error) {
      console.error('[Auth] Login error:', error.response?.status, error.response?.data || error.message);
      const message = error.response?.data?.detail || error.message || 'Login failed';
      toast.error(typeof message === 'string' ? message : 'Login failed. Check console.');
      return { success: false, error: message };
    }
  };

  const register = async (userData) => {
    try {
      console.log('[Auth] Registering with:', { email: userData.email, username: userData.username });
      const response = await authAPI.register(userData);
      console.log('[Auth] Register response:', response.data);
      const { access_token } = response.data;

      localStorage.setItem('token', access_token);
      setToken(access_token);

      await fetchUser();

      toast.success('Registered successfully!');
      return { success: true };
    } catch (error) {
      console.error('[Auth] Register error:', error.response?.status, error.response?.data || error.message);
      const message = error.response?.data?.detail || error.message || 'Registration failed';
      toast.error(typeof message === 'string' ? message : 'Registration failed. Check console for details.');
      return { success: false, error: message };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
    toast.success('Logged out successfully!');
  };

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};