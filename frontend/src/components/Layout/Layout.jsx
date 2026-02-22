import React from 'react';
import Navbar from './Navbar';

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-900">
      <Navbar />
      <main className="py-6">
        {children}
      </main>
    </div>
  );
};

export default Layout;