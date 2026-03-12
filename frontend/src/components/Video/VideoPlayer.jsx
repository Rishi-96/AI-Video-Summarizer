import React, { useRef, useState, useEffect } from 'react';
import { FiMaximize2, FiVolume2, FiVolumeX, FiPlay, FiPause } from 'react-icons/fi';

const VideoPlayer = ({ url, title, onProgress }) => {
  const videoRef = useRef(null);
  const containerRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [muted, setMuted] = useState(false);
  const [played, setPlayed] = useState(0);
  const [duration, setDuration] = useState(0);
  const [buffered, setBuffered] = useState(0);

  // Sync volume and muted state to video element
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.volume = volume;
      videoRef.current.muted = muted;
    }
  }, [volume, muted]);

  const handlePlayPause = () => {
    const video = videoRef.current;
    if (!video) return;
    if (playing) {
      video.pause();
    } else {
      video.play().catch(() => {});
    }
    setPlaying(!playing);
  };

  const handleTimeUpdate = () => {
    const video = videoRef.current;
    if (!video) return;
    const current = video.currentTime;
    const dur = video.duration || 1;
    const fraction = current / dur;
    setPlayed(fraction);

    // Buffered progress
    if (video.buffered.length > 0) {
      setBuffered(video.buffered.end(video.buffered.length - 1) / dur);
    }

    if (onProgress) {
      onProgress({ played: fraction, playedSeconds: current });
    }
  };

  const handleLoadedMetadata = () => {
    const video = videoRef.current;
    if (video) {
      setDuration(video.duration);
    }
  };

  const handleSeekChange = (e) => {
    const fraction = parseFloat(e.target.value);
    setPlayed(fraction);
    if (videoRef.current && duration > 0) {
      videoRef.current.currentTime = fraction * duration;
    }
  };

  const handleVolumeChange = (e) => {
    const v = parseFloat(e.target.value);
    setVolume(v);
    if (v > 0 && muted) setMuted(false);
  };

  const handleEnded = () => {
    setPlaying(false);
    setPlayed(0);
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
    }
  };

  const handleFullscreen = () => {
    const container = containerRef.current;
    if (!container) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else if (container.requestFullscreen) {
      container.requestFullscreen();
    } else if (container.webkitRequestFullscreen) {
      container.webkitRequestFullscreen();
    }
  };

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60).toString().padStart(2, '0');
    if (h > 0) {
      return `${h}:${m.toString().padStart(2, '0')}:${s}`;
    }
    return `${m}:${s}`;
  };

  return (
    <div ref={containerRef} className="bg-black rounded-xl overflow-hidden">
      {/* Video Element */}
      <div className="relative" style={{ paddingTop: '56.25%' }}>
        <video
          ref={videoRef}
          src={url}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={handleEnded}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          preload="metadata"
          playsInline
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            backgroundColor: '#000',
          }}
          onClick={handlePlayPause}
        />

        {/* Click-to-play overlay (only when paused) */}
        {!playing && (
          <div
            className="absolute inset-0 flex items-center justify-center cursor-pointer bg-black/30 transition-opacity hover:bg-black/40"
            onClick={handlePlayPause}
            style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}
          >
            <div className="w-16 h-16 rounded-full bg-blue-600/90 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <FiPlay size={28} className="text-white ml-1" />
            </div>
          </div>
        )}
      </div>

      {/* Video Controls */}
      <div className="bg-gray-900 px-4 py-3">
        {/* Progress Bar */}
        <div className="relative w-full h-1.5 bg-gray-700 rounded-full mb-3 cursor-pointer group">
          {/* Buffered */}
          <div
            className="absolute top-0 left-0 h-full bg-gray-600 rounded-full"
            style={{ width: `${buffered * 100}%` }}
          />
          {/* Played */}
          <div
            className="absolute top-0 left-0 h-full bg-blue-500 rounded-full transition-all"
            style={{ width: `${played * 100}%` }}
          />
          <input
            type="range"
            min={0}
            max={1}
            step={0.001}
            value={played}
            onChange={handleSeekChange}
            className="absolute top-0 left-0 w-full h-full opacity-0 cursor-pointer"
          />
        </div>

        <div className="flex items-center space-x-3">
          {/* Play/Pause Button */}
          <button
            onClick={handlePlayPause}
            className="text-white hover:text-blue-400 transition p-1"
          >
            {playing ? <FiPause size={20} /> : <FiPlay size={20} />}
          </button>

          {/* Volume Control */}
          <button
            onClick={() => setMuted(!muted)}
            className="text-white hover:text-blue-400 transition p-1"
          >
            {muted || volume === 0 ? <FiVolumeX size={18} /> : <FiVolume2 size={18} />}
          </button>

          {/* Volume Slider */}
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={muted ? 0 : volume}
            onChange={handleVolumeChange}
            className="w-20 h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            style={{
              background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${(muted ? 0 : volume) * 100}%, #374151 ${(muted ? 0 : volume) * 100}%, #374151 100%)`,
            }}
          />

          {/* Time */}
          <div className="flex-1 flex items-center justify-end">
            <span className="text-sm text-gray-400 font-mono">
              {formatTime(played * duration)} / {formatTime(duration)}
            </span>
          </div>

          {/* Fullscreen Button */}
          <button
            onClick={handleFullscreen}
            className="text-white hover:text-blue-400 transition p-1"
          >
            <FiMaximize2 size={17} />
          </button>
        </div>

        {/* Video Title */}
        {title && (
          <div className="mt-2 text-gray-300 text-sm font-medium truncate">
            {title}
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoPlayer;