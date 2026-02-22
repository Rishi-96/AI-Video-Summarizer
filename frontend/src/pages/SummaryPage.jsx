import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FiArrowLeft, FiMessageCircle, FiDownload, FiLoader } from 'react-icons/fi';
import { summariesAPI, chatAPI } from '../services/api';
import SummaryDisplay from '../components/Summary/SummaryDisplay';
import VideoPlayer from '../components/Video/VideoPlayer';
import toast from 'react-hot-toast';

const SummaryPage = () => {
  const { summaryId } = useParams();
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startingChat, setStartingChat] = useState(false);

  useEffect(() => {
    fetchSummary();
  }, [summaryId]);

  const fetchSummary = async () => {
    try {
      const response = await summariesAPI.getOne(summaryId);
      setSummary(response.data);
    } catch (error) {
      console.error('Error fetching summary:', error);
      toast.error('Failed to load summary');
    } finally {
      setLoading(false);
    }
  };

  const handleStartChat = async () => {
    setStartingChat(true);
    try {
      const response = await chatAPI.startSession(summaryId);
      navigate(`/chat/${response.data.session_id}`);
    } catch (error) {
      console.error('Error starting chat:', error);
      toast.error('Failed to start chat session');
    } finally {
      setStartingChat(false);
    }
  };

  const handleDownload = () => {
    // Create a text file with summary content
    const content = `
Video Summary
=============
${summary.text_summary}

Key Points
==========
${summary.key_points?.join('\n')}

Transcript Preview
=================
${summary.transcript}

Generated on: ${new Date(summary.created_at).toLocaleString()}
    `;
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `summary-${summaryId}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success('Summary downloaded!');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-white text-lg">Loading summary...</p>
        </div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="text-center">
          <p className="text-white text-lg">Summary not found</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center text-gray-400 hover:text-white transition"
        >
          <FiArrowLeft className="mr-2" />
          Back to Dashboard
        </button>
        
        <div className="flex items-center space-x-3">
          <button
            onClick={handleDownload}
            className="flex items-center px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
          >
            <FiDownload className="mr-2" />
            Download
          </button>
          
          <button
            onClick={handleStartChat}
            disabled={startingChat}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {startingChat ? (
              <>
                <FiLoader className="animate-spin mr-2" />
                Starting...
              </>
            ) : (
              <>
                <FiMessageCircle className="mr-2" />
                Chat About Video
              </>
            )}
          </button>
        </div>
      </div>

      {/* Video Player (if video exists) */}
      {summary.video_info?.path && (
        <div className="mb-8">
          <VideoPlayer 
            url={`http://localhost:8000/${summary.video_info.path}`}
            title={summary.video_info.filename}
          />
        </div>
      )}

      {/* Summary Display */}
      <SummaryDisplay summary={summary} />
    </div>
  );
};

export default SummaryPage;