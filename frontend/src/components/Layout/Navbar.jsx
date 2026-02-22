import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { FiLogOut, FiUser, FiVideo, FiHome, FiUpload } from 'react-icons/fi';

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="bg-gray-800 border-b border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <Link to="/" className="flex items-center">
              <FiVideo className="h-8 w-8 text-blue-500" />
              <span className="ml-2 text-xl font-bold text-white">AI Summarizer</span>
            </Link>
            
            <div className="hidden sm:ml-6 sm:flex sm:space-x-4">
              <Link
                to="/dashboard"
                className="flex items-center px-3 py-2 text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700 rounded-md"
              >
                <FiHome className="mr-1" />
                Dashboard
              </Link>
              
              <Link
                to="/upload"
                className="flex items-center px-3 py-2 text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700 rounded-md"
              >
                <FiUpload className="mr-1" />
                Upload
              </Link>
            </div>
          </div>
          
          <div className="flex items-center">
            <div className="flex items-center mr-4">
              <FiUser className="h-5 w-5 text-gray-400" />
              <span className="ml-2 text-sm text-gray-300">{user?.username}</span>
            </div>
            
            <button
              onClick={handleLogout}
              className="flex items-center px-3 py-2 text-sm font-medium text-gray-300 hover:text-white hover:bg-gray-700 rounded-md"
            >
              <FiLogOut className="mr-1" />
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;