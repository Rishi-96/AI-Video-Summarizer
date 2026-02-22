import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FiArrowLeft, FiInfo } from 'react-icons/fi';
import { summariesAPI } from '../services/api';
import ChatInterface from '../components/Chat/ChatInterface';
import toast from 'react-hot-toast';

const ChatPage = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSummaryInfo();
  }, []);

  const fetchSummaryInfo = async () => {
    try {
      // Extract summaryId from sessionId (you might want to store this mapping)
      // For now, we'll just fetch a default summary
      const response = await summariesAPI.getHistory();
      if (response.data.summaries && response.data.summaries.length > 0) {
        setSummary(response.data.summaries[0]);
      }
    } catch (error) {
      console.error('Error fetching summary:', error);
      toast.error('Failed to load chat context');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center text-gray-400 hover:text-white transition"
        >
          <FiArrowLeft className="mr-2" />
          Back
        </button>
        
        <div className="flex items-center bg-blue-600/10 text-blue-400 px-4 py-2 rounded-lg">
          <FiInfo className="mr-2" />
          <span className="text-sm">Ask questions about your video</span>
        </div>
      </div>

      {/* Chat Interface */}
      <ChatInterface sessionId={sessionId} summary={summary} />
    </div>
  );
};

export default ChatPage;