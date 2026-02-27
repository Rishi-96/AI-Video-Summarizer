import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { FiLogOut, FiVideo, FiHome, FiUpload } from 'react-icons/fi';
import { motion } from 'framer-motion';

const Navbar = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    window.location.href = '/';
  };

  const getInitial = (name) => {
    return name ? name.charAt(0).toUpperCase() : '?';
  };

  return (
    <nav className="glass-navbar border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="flex items-center group">
              <div className="bg-blue-600/20 p-2 rounded-xl group-hover:bg-blue-600/30 transition-colors">
                <FiVideo className="h-6 w-6 text-blue-500" />
              </div>
              <span className="ml-3 text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400 group-hover:to-white transition-all">AI Summarizer</span>
            </Link>

            <div className="hidden sm:ml-10 sm:flex sm:space-x-8">
              <Link
                to="/dashboard"
                className={`nav-link py-5 flex items-center ${location.pathname === '/dashboard' ? 'nav-link-active text-white' : ''}`}
              >
                <FiHome className="mr-2 h-4 w-4" />
                Dashboard
              </Link>

              <Link
                to="/upload"
                className={`nav-link py-5 flex items-center ${location.pathname === '/upload' ? 'nav-link-active text-white' : ''}`}
              >
                <FiUpload className="mr-2 h-4 w-4" />
                Upload
              </Link>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="hidden sm:flex items-center gap-3 bg-gray-800/50 py-1.5 px-3 rounded-full border border-gray-700/50 hover:bg-gray-800/80 transition-colors">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-sm font-bold text-white shadow-inner">
                {getInitial(user?.username)}
              </div>
              <span className="text-sm font-medium text-gray-200 pr-1">{user?.username}</span>
            </div>

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleLogout}
              className="flex items-center px-4 py-2 text-sm font-medium text-red-400 hover:text-white hover:bg-red-500/20 rounded-xl transition-colors border border-transparent hover:border-red-500/30"
            >
              <FiLogOut className="mr-2 h-4 w-4" />
              Logout
            </motion.button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;