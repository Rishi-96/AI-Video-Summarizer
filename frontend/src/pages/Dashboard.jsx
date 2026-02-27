import React, { useEffect } from 'react';
import { useVideo } from '../context/VideoContext';
import { useAuth } from '../context/AuthContext';
import VideoList from '../components/Video/VideoList';
import SummaryHistory from '../components/Summary/SummaryHistory';
import { FiVideo, FiFileText, FiActivity } from 'react-icons/fi';
import DashboardCard from '../components/Dashboard/DashboardCard';
import SkeletonLoader from '../components/Dashboard/SkeletonLoader';
import EmptyState from '../components/Dashboard/EmptyState';
import { motion, AnimatePresence } from 'framer-motion';

const Dashboard = () => {
  const { videos, summaries, fetchVideos, fetchSummaries, loading: videoLoading } = useVideo();
  const { user } = useAuth();

  useEffect(() => {
    fetchVideos();
    fetchSummaries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const processingCount = videos.filter(v => v.status === 'processing').length;
  const isCompletelyEmpty = videos.length === 0 && !videoLoading;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Header section with fade in */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold text-white mb-2">Welcome back, {user?.username}</h1>
        <p className="text-gray-400">Here's what's happening with your video summaries today.</p>
      </motion.div>

      <AnimatePresence mode="wait">
        {videoLoading ? (
          <motion.div key="loader" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <SkeletonLoader />
          </motion.div>
        ) : isCompletelyEmpty ? (
          <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <EmptyState />
          </motion.div>
        ) : (
          <motion.div
            key="content"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="space-y-12"
          >
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <DashboardCard
                title="Total Videos"
                value={videos.length}
                subtitle="Uploaded via dashboard"
                icon={FiVideo}
                gradient="from-blue-500 to-indigo-600"
                delay={0.1}
              />
              <DashboardCard
                title="Total Summaries"
                value={summaries.length}
                subtitle="AI-generated insights"
                icon={FiFileText}
                gradient="from-purple-500 to-pink-600"
                delay={0.2}
              />
              <DashboardCard
                title="Processing"
                value={processingCount}
                subtitle={processingCount > 0 ? "Analyzing right now" : "All caught up"}
                icon={FiActivity}
                gradient="from-emerald-400 to-teal-500"
                delay={0.3}
              />
            </div>

            {/* Video & Summary Sections */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 items-start">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.4 }}
                className="space-y-6"
              >
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                    <FiVideo className="text-blue-400" /> Recent Videos
                  </h2>
                </div>
                {videos.length > 0 ? (
                  <div className="bg-gray-800/30 rounded-2xl p-4 border border-gray-700/50 backdrop-blur-sm shadow-lg">
                    <VideoList videos={videos.slice(0, 3)} onDelete={fetchVideos} />
                  </div>
                ) : (
                  <div className="p-8 text-center bg-gray-800/30 rounded-2xl border border-gray-700/50">
                    <p className="text-gray-400">No videos uploaded yet.</p>
                  </div>
                )}
              </motion.div>

              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.5, delay: 0.5 }}
                className="space-y-6"
              >
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                    <FiFileText className="text-purple-400" /> Recent Summaries
                  </h2>
                </div>
                {summaries.length > 0 ? (
                  <div className="bg-gray-800/30 rounded-2xl p-4 border border-gray-700/50 backdrop-blur-sm shadow-lg">
                    <SummaryHistory summaries={summaries.slice(0, 5)} />
                  </div>
                ) : (
                  <div className="p-8 text-center bg-gray-800/30 rounded-2xl border border-gray-700/50">
                    <p className="text-gray-400">No summaries generated yet.</p>
                  </div>
                )}
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Dashboard;