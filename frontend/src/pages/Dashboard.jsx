import React, { useEffect } from 'react';
import { useVideo } from '../context/VideoContext';
import VideoList from '../components/Video/VideoList';
import SummaryHistory from '../components/Summary/SummaryHistory';
import { FiVideo, FiFileText } from 'react-icons/fi';

const Dashboard = () => {
  const { videos, summaries, fetchVideos, fetchSummaries, loading } = useVideo();

  useEffect(() => {
    fetchVideos();
    fetchSummaries();
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Stats Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gradient-to-br from-blue-600 to-blue-800 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm">Total Videos</p>
              <p className="text-3xl font-bold text-white">{videos.length}</p>
            </div>
            <FiVideo className="h-10 w-10 text-blue-300" />
          </div>
        </div>

        <div className="bg-gradient-to-br from-purple-600 to-purple-800 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm">Total Summaries</p>
              <p className="text-3xl font-bold text-white">{summaries.length}</p>
            </div>
            <FiFileText className="h-10 w-10 text-purple-300" />
          </div>
        </div>

        <div className="bg-gradient-to-br from-green-600 to-green-800 rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-100 text-sm">Processing</p>
              <p className="text-3xl font-bold text-white">
                {videos.filter(v => v.status === 'processing').length}
              </p>
            </div>
            <div className="animate-pulse h-10 w-10 rounded-full bg-green-300 flex items-center justify-center">
              <div className="h-4 w-4 bg-green-600 rounded-full"></div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Videos */}
      <div className="mb-12">
        <h2 className="text-2xl font-bold text-white mb-6">Recent Videos</h2>
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mx-auto"></div>
          </div>
        ) : (
          <VideoList videos={videos.slice(0, 3)} onDelete={fetchVideos} />
        )}
      </div>

      {/* Recent Summaries */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-6">Recent Summaries</h2>
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mx-auto"></div>
          </div>
        ) : (
          <SummaryHistory summaries={summaries.slice(0, 5)} />
        )}
      </div>
    </div>
  );
};

export default Dashboard;