import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { FiUploadCloud, FiLink } from 'react-icons/fi';
import { useVideo } from '../../context/VideoContext';

const VideoUploader = ({ onUploadComplete }) => {
  const { uploadVideo, uploadYouTubeVideo, loading, uploadProgress } = useVideo();
  const [activeTab, setActiveTab] = useState('file'); // 'file' or 'youtube'
  const [youtubeUrl, setYoutubeUrl] = useState('');

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    try {
      const result = await uploadVideo(file);
      if (onUploadComplete) {
        onUploadComplete(result);
      }
    } catch (error) {
      console.error('Upload failed:', error);
    }
  }, [uploadVideo, onUploadComplete]);

  const handleYouTubeSubmit = async (e) => {
    e.preventDefault();
    if (!youtubeUrl) return;
    try {
      const result = await uploadYouTubeVideo(youtubeUrl);
      if (onUploadComplete) {
        onUploadComplete(result);
      }
      setYoutubeUrl('');
    } catch (error) {
      console.error('YouTube upload failed', error);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.avi', '.mov', '.mkv', '.webm']
    },
    maxFiles: 1,
    maxSize: 500 * 1024 * 1024, // 500MB
  });

  return (
    <div className="bg-gray-800 rounded-xl p-8">
      {/* Tabs */}
      <div className="flex border-b border-gray-700 mb-6">
        <button
          onClick={() => setActiveTab('file')}
          className={`flex-1 py-3 text-center text-sm font-medium transition-colors border-b-2 ${activeTab === 'file'
              ? 'border-blue-500 text-blue-500'
              : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
        >
          <FiUploadCloud className="inline-block mr-2" />
          File Upload
        </button>
        <button
          onClick={() => setActiveTab('youtube')}
          className={`flex-1 py-3 text-center text-sm font-medium transition-colors border-b-2 ${activeTab === 'youtube'
              ? 'border-blue-500 text-blue-500'
              : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
        >
          <FiLink className="inline-block mr-2" />
          YouTube URL
        </button>
      </div>

      {activeTab === 'file' ? (
        <div
          {...getRootProps()}
          className={`border-4 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-300 ${isDragActive
              ? 'border-blue-500 bg-blue-500/10'
              : 'border-gray-600 hover:border-blue-400 hover:bg-gray-700'
            }`}
        >
          <input {...getInputProps()} />
          <FiUploadCloud className="text-6xl mx-auto mb-4 text-blue-500" />

          {isDragActive ? (
            <p className="text-xl text-white">Drop your video here...</p>
          ) : (
            <div>
              <p className="text-xl text-white mb-2">
                Drag & drop your video here
              </p>
              <p className="text-gray-400 mb-4">or click to browse</p>
              <p className="text-sm text-gray-500">
                Supported formats: MP4, AVI, MOV, MKV (Max 500MB)
              </p>
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={handleYouTubeSubmit} className="py-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Paste YouTube Video Link
          </label>
          <div className="flex gap-4">
            <input
              type="url"
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              className="flex-1 input-primary"
              required
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !youtubeUrl}
              className="btn-primary flex items-center whitespace-nowrap disabled:opacity-50"
            >
              {loading ? 'Processing...' : 'Add Video'}
            </button>
          </div>
        </form>
      )}

      {loading && activeTab === 'file' && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Uploading...</span>
            <span className="text-sm text-gray-400">{uploadProgress}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {loading && activeTab === 'youtube' && (
        <div className="mt-6 text-center text-sm text-gray-400">
          <div className="animate-pulse flex items-center justify-center gap-2">
            <div className="w-4 h-4 rounded-full bg-blue-500"></div>
            Downloading from YouTube... this may take a moment.
          </div>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-500 text-center flex flex-col gap-1">
        <p>Your videos are processed securely and deleted after summarization</p>
        <p>Short YouTube videos (under 10 minutes) work best for fast processing.</p>
      </div>
    </div>
  );
};

export default VideoUploader;