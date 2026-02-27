import React, { createContext, useState, useContext, useCallback } from 'react';
import { videosAPI, summariesAPI } from '../services/api';
import toast from 'react-hot-toast';

const VideoContext = createContext();

export const useVideo = () => {
  const context = useContext(VideoContext);
  if (!context) throw new Error('useVideo must be used within a VideoProvider');
  return context;
};

// ─── polling helper ─────────────────────────────────────────────────────────
const POLL_INTERVAL_MS = 2500;
const POLL_TIMEOUT_MS = 10 * 60 * 1000; // 10 min

async function pollUntilDone(taskId, onStatusUpdate) {
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    const { data } = await summariesAPI.getTaskStatus(taskId);
    if (onStatusUpdate) onStatusUpdate(data.status);
    if (data.status === 'done') return data.summary_id;
    if (data.status === 'failed') throw new Error(data.error || 'Summarization failed');
  }
  throw new Error('Summarization timed out. The video may be too long.');
}

export const VideoProvider = ({ children }) => {
  const [videos, setVideos] = useState([]);
  const [summaries, setSummaries] = useState([]);
  const [currentVideo, setCurrentVideo] = useState(null);
  const [currentSummary, setCurrentSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [summaryStatus, setSummaryStatus] = useState(null); // 'pending' | 'processing' | 'done' | 'failed'

  // ── fetch videos ────────────────────────────────────────────────────────
  const fetchVideos = useCallback(async () => {
    try {
      setLoading(true);
      const response = await videosAPI.getAll();
      setVideos(response.data.videos || []);
    } catch (error) {
      console.error('Error fetching videos:', error);
      toast.error('Failed to fetch videos');
    } finally {
      setLoading(false);
    }
  }, []);

  // ── fetch summaries ─────────────────────────────────────────────────────
  const fetchSummaries = useCallback(async () => {
    try {
      setLoading(true);
      const response = await summariesAPI.getHistory();
      setSummaries(response.data.summaries || []);
    } catch (error) {
      console.error('Error fetching summaries:', error);
      toast.error('Failed to fetch summaries');
    } finally {
      setLoading(false);
    }
  }, []);

  // ── upload video ────────────────────────────────────────────────────────
  const uploadVideo = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    try {
      setLoading(true);
      setUploadProgress(0);
      const response = await videosAPI.upload(formData, setUploadProgress);
      toast.success('Video uploaded successfully!');
      await fetchVideos();
      return response.data;
    } catch (error) {
      console.error('Upload error:', error);
      const detail = error.response?.data?.detail;
      const msg = typeof detail === 'object' ? detail?.message : (detail || 'Upload failed');
      toast.error(msg);
      throw error;
    } finally {
      setLoading(false);
      setUploadProgress(0);
    }
  };

  // ── upload YouTube ──────────────────────────────────────────────────────
  const uploadYouTubeVideo = async (url) => {
    try {
      setLoading(true);
      const response = await videosAPI.uploadYouTube(url);
      toast.success('YouTube video downloaded!');
      await fetchVideos();
      return response.data;
    } catch (error) {
      console.error('YouTube upload error:', error);
      const detail = error.response?.data?.detail;
      const msg = typeof detail === 'object' ? detail?.message : (detail || 'YouTube upload failed');
      toast.error(msg);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // ── create summary (202 + poll) ─────────────────────────────────────────
  const createSummary = async (videoPath, summaryRatio = 0.3) => {
    try {
      setLoading(true);
      setSummaryStatus('pending');

      // 1. Enqueue the job (returns 202 + task_id)
      const { data: task } = await summariesAPI.create(videoPath, summaryRatio);
      toast.success('Summarization started — processing in background…');

      // 2. Poll until done
      const summaryId = await pollUntilDone(task.task_id, (status) => {
        setSummaryStatus(status);
      });

      // 3. Fetch the completed summary
      const { data: summary } = await summariesAPI.getOne(summaryId);
      toast.success('Summary ready!');
      await fetchSummaries();
      setCurrentSummary(summary);
      setSummaryStatus('done');
      return summary;

    } catch (error) {
      console.error('Summary error:', error);
      setSummaryStatus('failed');
      const detail = error.response?.data?.detail;
      const msg = typeof detail === 'object' ? detail?.message : (detail || error.message || 'Summary creation failed');
      toast.error(msg);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // ── delete video ────────────────────────────────────────────────────────
  const deleteVideo = async (fileId) => {
    try {
      setLoading(true);
      await videosAPI.delete(fileId);
      toast.success('Video deleted!');
      await fetchVideos();
      return true;
    } catch (error) {
      console.error('Delete error:', error);
      toast.error('Failed to delete video');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const value = {
    videos,
    summaries,
    currentVideo,
    currentSummary,
    loading,
    uploadProgress,
    summaryStatus,
    fetchVideos,
    fetchSummaries,
    uploadVideo,
    uploadYouTubeVideo,
    createSummary,
    deleteVideo,
    setCurrentVideo,
    setCurrentSummary,
  };

  return <VideoContext.Provider value={value}>{children}</VideoContext.Provider>;
};