import React, { createContext, useState, useContext, useCallback } from 'react';
import { videosAPI, summariesAPI } from '../services/api';
import toast from 'react-hot-toast';

const VideoContext = createContext();

export const useVideo = () => {
  const context = useContext(VideoContext);
  if (!context) {
    throw new Error('useVideo must be used within a VideoProvider');
  }
  return context;
};

export const VideoProvider = ({ children }) => {
  const [videos, setVideos] = useState([]);
  const [summaries, setSummaries] = useState([]);
  const [currentVideo, setCurrentVideo] = useState(null);
  const [currentSummary, setCurrentSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

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

  const uploadVideo = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      setLoading(true);
      setUploadProgress(0);

      const response = await videosAPI.upload(formData);
      
      toast.success('Video uploaded successfully!');
      await fetchVideos();
      
      return response.data;
    } catch (error) {
      console.error('Upload error:', error);
      toast.error(error.response?.data?.detail || 'Upload failed');
      throw error;
    } finally {
      setLoading(false);
      setUploadProgress(0);
    }
  };

  const createSummary = async (videoPath, summaryRatio = 0.3) => {
    try {
      setLoading(true);
      const response = await summariesAPI.create(videoPath, summaryRatio);
      
      toast.success('Summary created successfully!');
      await fetchSummaries();
      
      setCurrentSummary(response.data);
      return response.data;
    } catch (error) {
      console.error('Summary error:', error);
      toast.error(error.response?.data?.detail || 'Summary creation failed');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const deleteVideo = async (fileId) => {
    try {
      setLoading(true);
      await videosAPI.delete(fileId);
      
      toast.success('Video deleted successfully!');
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
    fetchVideos,
    fetchSummaries,
    uploadVideo,
    createSummary,
    deleteVideo,
    setCurrentVideo,
    setCurrentSummary,
  };

  return <VideoContext.Provider value={value}>{children}</VideoContext.Provider>;
};