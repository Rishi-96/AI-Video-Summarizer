import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

// Layout
import Layout from './components/Layout/Layout';

// Pages
import HomePage from './pages/HomePage';
import Dashboard from './pages/Dashboard';
import UploadPage from './pages/UploadPage';
import SummaryPage from './pages/SummaryPage';
import ChatPage from './pages/ChatPage';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import PrivateRoute from './components/Auth/PrivateRoute';

function App() {
  return (
    <>
      <Toaster 
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#363636',
            color: '#fff',
          },
          success: {
            duration: 3000,
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            duration: 4000,
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
      
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/" element={<HomePage />} />
        
        {/* Protected routes - Temporarily open without auth */}
        <Route path="/dashboard" element={
            <Layout>
              <Dashboard />
            </Layout>
        } />
        
        <Route path="/upload" element={
            <Layout>
              <UploadPage />
            </Layout>
        } />
        
        <Route path="/summary/:summaryId" element={
            <Layout>
              <SummaryPage />
            </Layout>
        } />
        
        <Route path="/chat/:sessionId" element={
            <Layout>
              <ChatPage />
            </Layout>
        } />
        
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </>
  );
}

export default App;