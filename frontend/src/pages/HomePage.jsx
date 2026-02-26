import React from 'react';
import { Link } from 'react-router-dom';
import { FiVideo, FiCpu, FiMessageCircle, FiArrowRight } from 'react-icons/fi';
import { useAuth } from '../context/AuthContext';

const HomePage = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <div className="text-center">
            <h1 className="text-5xl md:text-6xl font-extrabold text-white mb-6">
              AI Video Summarizer
            </h1>
            <p className="text-xl text-gray-300 mb-8 max-w-3xl mx-auto">
              Transform lengthy videos into concise, intelligent summaries with AI.
              Get key insights without watching the entire video.
            </p>
            
            <div className="flex justify-center space-x-4">
              <Link
                to="/dashboard"
                className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition"
              >
                Get Started
                <FiArrowRight className="ml-2" />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h2 className="text-3xl font-bold text-white text-center mb-12">
          Powerful Features
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-gray-800 rounded-xl p-8 text-center hover:transform hover:scale-105 transition">
            <div className="bg-blue-600/20 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
              <FiVideo className="h-8 w-8 text-blue-500" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              Smart Video Processing
            </h3>
            <p className="text-gray-400">
              Upload any video and our AI automatically extracts audio, transcribes content, and identifies key segments.
            </p>
          </div>

          <div className="bg-gray-800 rounded-xl p-8 text-center hover:transform hover:scale-105 transition">
            <div className="bg-purple-600/20 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
              <FiCpu className="h-8 w-8 text-purple-500" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              AI-Powered Summaries
            </h3>
            <p className="text-gray-400">
              Get concise, context-aware summaries using state-of-the-art language models.
            </p>
          </div>

          <div className="bg-gray-800 rounded-xl p-8 text-center hover:transform hover:scale-105 transition">
            <div className="bg-green-600/20 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
              <FiMessageCircle className="h-8 w-8 text-green-500" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              Interactive Chat
            </h3>
            <p className="text-gray-400">
              Ask questions about your video content and get instant answers from our AI assistant.
            </p>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h2 className="text-3xl font-bold text-white text-center mb-12">
          How It Works
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[
            { step: '1', title: 'Upload Video', desc: 'Upload your video file (MP4, AVI, MOV, MKV)' },
            { step: '2', title: 'AI Processing', desc: 'Our AI transcribes and analyzes the content' },
            { step: '3', title: 'Get Summary', desc: 'Receive a concise text summary and key points' },
            { step: '4', title: 'Chat & Explore', desc: 'Ask questions and dive deeper into content' }
          ].map((item) => (
            <div key={item.step} className="relative">
              <div className="bg-gray-800 rounded-xl p-6 text-center">
                <div className="bg-blue-600 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 text-white font-bold text-xl">
                  {item.step}
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">
                  {item.title}
                </h3>
                <p className="text-gray-400 text-sm">
                  {item.desc}
                </p>
              </div>
              {item.step !== '4' && (
                <div className="hidden md:block absolute top-1/2 -right-2 text-gray-600 text-2xl">
                  →
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* CTA Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-12 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Get Started?
          </h2>
          <p className="text-xl text-blue-100 mb-8">
            Join thousands of users who save time with AI-powered video summaries
          </p>
          <Link
            to="/dashboard"
            className="inline-flex items-center px-8 py-4 bg-white text-blue-600 font-medium rounded-lg hover:bg-gray-100 transition text-lg"
          >
            Get Started
            <FiArrowRight className="ml-2" />
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <p className="text-center text-gray-500 text-sm">
            © 2024 AI Video Summarizer. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;