import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { FiUploadCloud, FiFile } from 'react-icons/fi';
import { useVideo } from '../../context/VideoContext';

const VideoUploader = ({ onUploadComplete }) => {
  const { uploadVideo, loading, uploadProgress } = useVideo();

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
      <div
        {...getRootProps()}
        className={`border-4 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-300 ${
          isDragActive 
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

      {loading && (
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

      <div className="mt-4 text-xs text-gray-500 text-center">
        <p>Your videos are processed securely and deleted after summarization</p>
      </div>
    </div>
  );
};

export default VideoUploader;