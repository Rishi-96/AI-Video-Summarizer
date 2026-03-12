import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FiArrowLeft, FiMessageCircle, FiDownload, FiLoader, FiFilm, FiVideo } from 'react-icons/fi';
import { summariesAPI, chatAPI } from '../services/api';
import SummaryDisplay from '../components/Summary/SummaryDisplay';
import VideoPlayer from '../components/Video/VideoPlayer';
import toast from 'react-hot-toast';

const API_BASE = process.env.REACT_APP_API_URL || `http://${window.location.hostname}:8000`;


const SummaryPage = () => {
  const { summaryId } = useParams();
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startingChat, setStartingChat] = useState(false);
  const [activeTab, setActiveTab] = useState('original'); // 'original' | 'summary'

  const fetchSummary = useCallback(async () => {
    try {
      const response = await summariesAPI.getOne(summaryId);
      setSummary(response.data);
      // Auto-switch to summary video tab if available
      if (response.data.has_summary_video) {
        setActiveTab('summary');
      }
    } catch (error) {
      console.error('Error fetching summary:', error);
      toast.error('Failed to load summary');
    } finally {
      setLoading(false);
    }
  }, [summaryId]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

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

  const handleDownloadSummaryVideo = () => {
    if (!summary?.has_summary_video) return;
    const url = summariesAPI.getSummaryVideoUrl(summaryId);
    const a = document.createElement('a');
    a.href = url;
    a.download = `summary-video-${summaryId.substring(0, 8)}.mp4`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    toast.success('Summary video download started!');
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

  const originalVideoUrl = summary.video_info?.file_id
    ? `${API_BASE}/api/videos/stream/${summary.video_info.file_id}?token=${encodeURIComponent(localStorage.getItem('token') || '')}`
    : null;

  const summaryVideoUrl = summary.has_summary_video
    ? summariesAPI.getSummaryVideoUrl(summaryId)
    : null;

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
          {summary.has_summary_video && (
            <button
              onClick={handleDownloadSummaryVideo}
              className="flex items-center px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 transition shadow-lg shadow-purple-500/20"
            >
              <FiFilm className="mr-2" />
              Download Summary Video
            </button>
          )}

          <button
            onClick={handleDownload}
            className="flex items-center px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
          >
            <FiDownload className="mr-2" />
            Download Text
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

      {/* Video Player Section */}
      {(originalVideoUrl || summaryVideoUrl) && (
        <div className="mb-8">
          {/* Video Tab Switcher */}
          {originalVideoUrl && summaryVideoUrl && (
            <div className="flex mb-4">
              <button
                onClick={() => setActiveTab('original')}
                className={`flex items-center px-5 py-2.5 rounded-l-xl text-sm font-medium transition-all duration-200 ${
                  activeTab === 'original'
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
                }`}
              >
                <FiVideo className="mr-2" />
                Original Video
              </button>
              <button
                onClick={() => setActiveTab('summary')}
                className={`flex items-center px-5 py-2.5 rounded-r-xl text-sm font-medium transition-all duration-200 ${
                  activeTab === 'summary'
                    ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg shadow-purple-500/30'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'
                }`}
              >
                <FiFilm className="mr-2" />
                Summarized Video
                <span className="ml-2 px-2 py-0.5 bg-white/20 rounded-full text-xs">
                  AI
                </span>
              </button>
            </div>
          )}

          {/* Video Players */}
          {activeTab === 'original' && originalVideoUrl && (
            <div>
              <VideoPlayer
                url={originalVideoUrl}
                title={summary.video_info?.filename || 'Original Video'}
              />
            </div>
          )}

          {activeTab === 'summary' && summaryVideoUrl && (
            <div>
              <div className="relative">
                <VideoPlayer
                  url={summaryVideoUrl}
                  title="AI-Generated Summary Video"
                />
                {/* Gradient overlay badge */}
                <div className="absolute top-3 left-3 flex items-center px-3 py-1.5 bg-gradient-to-r from-purple-600/90 to-pink-600/90 backdrop-blur-sm rounded-lg shadow-lg">
                  <FiFilm className="mr-1.5 text-white" size={14} />
                  <span className="text-white text-xs font-semibold tracking-wide">SUMMARIZED</span>
                </div>
              </div>
              {summary.summary_video_size && (
                <div className="mt-2 text-sm text-gray-500 text-right">
                  Summary video size: {(summary.summary_video_size / (1024 * 1024)).toFixed(2)} MB
                </div>
              )}
            </div>
          )}

          {/* Show only original if no summary video */}
          {!summaryVideoUrl && originalVideoUrl && activeTab === 'original' && (
            <div className="mt-3 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
              <p className="text-yellow-400 text-sm flex items-center">
                <FiFilm className="mr-2" />
                Summary video was not generated for this summary. Re-summarize to generate one.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Summary Display */}
      <SummaryDisplay summary={summary} />
    </div>
  );
};

export default SummaryPage;