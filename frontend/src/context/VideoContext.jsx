import React, { createContext, useState, useContext, useCallback } from 'react';
import { videosAPI, summariesAPI } from '../services/api';
import toast from 'react-hot-toast';

const VideoContext = createContext();

export const useVideo = () => {
  const context = useContext(VideoContext);
  if (!context) throw new Error('useVideo must be used within a VideoProvider');
  return context;
};

// ─── SSE progress helper (real-time, replaces 5s polling) ────────────────────
const SSE_TIMEOUT_MS = 20 * 60 * 1000; // 20 min timeout

function watchProgressSSE(taskId, onProgressUpdate) {
  return new Promise((resolve, reject) => {
    const url = summariesAPI.getProgressUrl(taskId);
    const eventSource = new EventSource(url);
    const timeout = setTimeout(() => {
      eventSource.close();
      reject(new Error('Summarization timed out. The video may be too long.'));
    }, SSE_TIMEOUT_MS);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.error) {
          eventSource.close();
          clearTimeout(timeout);
          reject(new Error(data.error));
          return;
        }
        if (onProgressUpdate) onProgressUpdate(data);
        if (data.status === 'done') {
          eventSource.close();
          clearTimeout(timeout);
          resolve(data.summary_id);
        }
        if (data.status === 'failed') {
          eventSource.close();
          clearTimeout(timeout);
          reject(new Error(data.error || 'Summarization failed'));
        }
      } catch (e) {
        console.error('SSE parse error:', e);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      clearTimeout(timeout);
      // Fallback to polling if SSE fails
      console.warn('SSE connection lost, falling back to polling...');
      pollUntilDone(taskId, (status) => {
        if (onProgressUpdate) onProgressUpdate({ status, progress: 0, step: '' });
      }).then(resolve).catch(reject);
    };
  });
}

// ─── Polling fallback ────────────────────────────────────────────────────────
const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 20 * 60 * 1000;

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
  const [summaryStatus, setSummaryStatus] = useState(null);
  const [summaryProgress, setSummaryProgress] = useState({ progress: 0, step: '' }); // NEW


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

  // ── create summary (202 + SSE progress) ──────────────────────────────────
  const createSummary = async (fileId, summaryRatio = 0.3) => {
    try {
      setLoading(true);
      setSummaryStatus('pending');
      setSummaryProgress({ progress: 0, step: 'Queuing...' });

      // 1. Enqueue the job (returns 202 + task_id)
      const { data: task } = await summariesAPI.create(fileId, summaryRatio);
      toast.success('Summarization started — processing in background...');

      // 2. Watch progress via SSE (real-time 1s updates vs old 5s polling)
      const summaryId = await watchProgressSSE(task.task_id, (data) => {
        setSummaryStatus(data.status);
        setSummaryProgress({
          progress: data.progress || 0,
          step: data.step || data.status || '',
        });
      });

      // 3. Fetch the completed summary
      const { data: summary } = await summariesAPI.getOne(summaryId);
      toast.success('Summary ready!');
      await fetchSummaries();
      setCurrentSummary(summary);
      setSummaryStatus('done');
      setSummaryProgress({ progress: 100, step: 'Complete' });
      return summary;

    } catch (error) {
      console.error('Summary error:', error);
      setSummaryStatus('failed');
      setSummaryProgress({ progress: 0, step: 'Failed' });
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
    summaryProgress,
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