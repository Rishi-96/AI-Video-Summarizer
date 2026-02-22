import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FiVideo, FiTrash2, FiClock, FiBarChart2 } from 'react-icons/fi';
import { formatDistanceToNow } from 'date-fns';
import { useVideo } from '../../context/VideoContext';

const VideoList = ({ videos, onDelete }) => {
  const navigate = useNavigate();
  const { deleteVideo } = useVideo();

  const handleDelete = async (fileId, e) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this video?')) {
      const success = await deleteVideo(fileId);
      if (success && onDelete) {
        onDelete();
      }
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (!videos || videos.length === 0) {
    return (
      <div className="text-center py-12 bg-gray-800 rounded-xl">
        <FiVideo className="mx-auto h-12 w-12 text-gray-600" />
        <h3 className="mt-2 text-sm font-medium text-gray-400">No videos</h3>
        <p className="mt-1 text-sm text-gray-500">
          Get started by uploading your first video.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {videos.map((video) => (
        <div
          key={video.file_id}
          onClick={() => navigate(`/summary/${video.file_id}`)}
          className="bg-gray-800 rounded-xl overflow-hidden hover:ring-2 hover:ring-blue-500 cursor-pointer transition-all"
        >
          {/* Video Thumbnail */}
          <div className="relative h-40 bg-gray-900 flex items-center justify-center">
            <FiVideo className="h-12 w-12 text-gray-700" />
            <div className="absolute bottom-2 right-2 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded">
              {video.duration ? `${Math.round(video.duration)}s` : '--:--'}
            </div>
          </div>

          {/* Video Info */}
          <div className="p-4">
            <h3 className="text-white font-medium mb-2 truncate">
              {video.original_name || video.filename}
            </h3>
            
            <div className="space-y-1 text-sm">
              <div className="flex items-center text-gray-400">
                <FiClock className="mr-2 h-4 w-4" />
                <span>
                  {formatDistanceToNow(new Date(video.created_at), { addSuffix: true })}
                </span>
              </div>
              
              <div className="flex items-center text-gray-400">
                <FiBarChart2 className="mr-2 h-4 w-4" />
                <span>{formatFileSize(video.file_size)}</span>
              </div>
            </div>

            {/* Status Badge */}
            <div className="mt-3 flex items-center justify-between">
              <span className={`px-2 py-1 text-xs rounded-full ${
                video.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                video.status === 'processing' ? 'bg-yellow-500/20 text-yellow-400' :
                video.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                'bg-gray-600/20 text-gray-400'
              }`}>
                {video.status || 'uploaded'}
              </span>

              <button
                onClick={(e) => handleDelete(video.file_id, e)}
                className="p-2 text-gray-400 hover:text-red-500 transition"
              >
                <FiTrash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default VideoList;