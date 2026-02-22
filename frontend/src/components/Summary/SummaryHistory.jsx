import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FiFileText, FiMessageCircle, FiCalendar, FiClock } from 'react-icons/fi';
import { formatDistanceToNow } from 'date-fns';

const SummaryHistory = ({ summaries }) => {
  const navigate = useNavigate();

  if (!summaries || summaries.length === 0) {
    return (
      <div className="text-center py-12 bg-gray-800 rounded-xl">
        <FiFileText className="mx-auto h-12 w-12 text-gray-600" />
        <h3 className="mt-2 text-sm font-medium text-gray-400">No summaries yet</h3>
        <p className="mt-1 text-sm text-gray-500">
          Upload and summarize a video to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {summaries.map((summary) => (
        <div
          key={summary.summary_id}
          className="bg-gray-800 rounded-xl p-6 hover:ring-2 hover:ring-blue-500 cursor-pointer transition-all"
          onClick={() => navigate(`/summary/${summary.summary_id}`)}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="text-white font-medium mb-2">
                {summary.video_info?.filename || 'Video Summary'}
              </h3>
              
              <p className="text-gray-400 text-sm mb-3 line-clamp-2">
                {summary.text_summary}
              </p>
              
              <div className="flex items-center space-x-4 text-xs text-gray-500">
                <span className="flex items-center">
                  <FiCalendar className="mr-1 h-3 w-3" />
                  {formatDistanceToNow(new Date(summary.created_at), { addSuffix: true })}
                </span>
                <span className="flex items-center">
                  <FiClock className="mr-1 h-3 w-3" />
                  {summary.segments?.length || 0} segments
                </span>
                <span className="flex items-center">
                  <FiMessageCircle className="mr-1 h-3 w-3" />
                  {summary.key_points?.length || 0} key points
                </span>
              </div>
            </div>

            <div className="ml-4">
              <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded-full">
                {summary.language || 'EN'}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default SummaryHistory;