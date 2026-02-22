import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import VideoUploader from '../components/Video/VideoUploader';
import { useVideo } from '../context/VideoContext';

const UploadPage = () => {
  const [uploadedVideo, setUploadedVideo] = useState(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const { createSummary } = useVideo();
  const navigate = useNavigate();

  const handleUploadComplete = (result) => {
    setUploadedVideo(result);
  };

  const handleSummarize = async () => {
    if (!uploadedVideo) return;

    setIsSummarizing(true);
    try {
      const summary = await createSummary(uploadedVideo.path, 0.3);
      navigate(`/summary/${summary.summary_id}`);
    } catch (error) {
      console.error('Summarization failed:', error);
    } finally {
      setIsSummarizing(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">
          Upload Your Video
        </h1>
        <p className="text-gray-400">
          Upload a video and let AI create a smart summary for you
        </p>
      </div>

      <VideoUploader onUploadComplete={handleUploadComplete} />

      {uploadedVideo && (
        <div className="mt-8 bg-gray-800 rounded-xl p-6">
          <h3 className="text-lg font-medium text-white mb-4">
            Upload Complete
          </h3>
          
          <div className="bg-gray-700 rounded-lg p-4 mb-4">
            <p className="text-gray-300">
              <span className="font-medium">File:</span> {uploadedVideo.original_name}
            </p>
            <p className="text-gray-300">
              <span className="font-medium">Size:</span> {uploadedVideo.size_mb} MB
            </p>
          </div>

          <div className="flex justify-end space-x-4">
            <button
              onClick={() => setUploadedVideo(null)}
              className="px-6 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
            >
              Upload Another
            </button>
            <button
              onClick={handleSummarize}
              disabled={isSummarizing}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center"
            >
              {isSummarizing ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                  Summarizing...
                </>
              ) : (
                'Generate Summary'
              )}
            </button>
          </div>
        </div>
      )}

      <div className="mt-12 bg-blue-600/10 border border-blue-500/30 rounded-xl p-6">
        <h4 className="text-blue-400 font-medium mb-2">📌 Note</h4>
        <p className="text-gray-300 text-sm">
          The summarization process may take a few minutes depending on the video length. 
          You'll be redirected to the summary page once it's complete.
        </p>
      </div>
    </div>
  );
};

export default UploadPage;