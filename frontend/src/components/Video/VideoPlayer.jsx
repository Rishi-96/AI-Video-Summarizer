import React from 'react';
import ReactPlayer from 'react-player';
import { FiMaximize2, FiVolume2, FiVolumeX } from 'react-icons/fi';

const VideoPlayer = ({ url, title, onProgress }) => {
  const [playing, setPlaying] = React.useState(false);
  const [volume, setVolume] = React.useState(0.8);
  const [muted, setMuted] = React.useState(false);
  const [played, setPlayed] = React.useState(0);
  const [duration, setDuration] = React.useState(0);
  const playerRef = React.useRef(null);

  const handleProgress = (state) => {
    setPlayed(state.played);
    if (onProgress) {
      onProgress(state);
    }
  };

  const handleSeekChange = (e) => {
    setPlayed(parseFloat(e.target.value));
    playerRef.current.seekTo(parseFloat(e.target.value));
  };

  const formatTime = (seconds) => {
    const date = new Date(seconds * 1000);
    const hh = date.getUTCHours();
    const mm = date.getUTCMinutes();
    const ss = date.getUTCSeconds().toString().padStart(2, '0');
    if (hh) {
      return `${hh}:${mm.toString().padStart(2, '0')}:${ss}`;
    }
    return `${mm}:${ss}`;
  };

  return (
    <div className="bg-black rounded-xl overflow-hidden">
      <div className="relative pt-[56.25%]"> {/* 16:9 Aspect Ratio */}
        <ReactPlayer
          ref={playerRef}
          url={url}
          width="100%"
          height="100%"
          style={{ position: 'absolute', top: 0, left: 0 }}
          playing={playing}
          volume={volume}
          muted={muted}
          onProgress={handleProgress}
          onDuration={setDuration}
          config={{
            file: {
              attributes: {
                controlsList: 'nodownload'
              }
            }
          }}
        />
      </div>

      {/* Video Controls */}
      <div className="bg-gray-900 p-4">
        <div className="flex items-center space-x-4">
          {/* Play/Pause Button */}
          <button
            onClick={() => setPlaying(!playing)}
            className="text-white hover:text-blue-400 transition"
          >
            {playing ? (
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M10 9v6h2V9h-2zm4 0v6h2V9h-2z" />
              </svg>
            ) : (
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>

          {/* Volume Control */}
          <button
            onClick={() => setMuted(!muted)}
            className="text-white hover:text-blue-400 transition"
          >
            {muted ? <FiVolumeX size={20} /> : <FiVolume2 size={20} />}
          </button>

          {/* Volume Slider */}
          <input
            type="range"
            min={0}
            max={1}
            step={0.1}
            value={volume}
            onChange={(e) => setVolume(parseFloat(e.target.value))}
            className="w-24 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />

          {/* Progress Bar */}
          <div className="flex-1 flex items-center space-x-2">
            <span className="text-sm text-gray-400">
              {formatTime(played * duration)}
            </span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.001}
              value={played}
              onChange={handleSeekChange}
              className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
            />
            <span className="text-sm text-gray-400">
              {formatTime(duration)}
            </span>
          </div>

          {/* Fullscreen Button */}
          <button
            onClick={() => {
              const player = playerRef.current;
              if (player) {
                const internalPlayer = player.getInternalPlayer();
                if (internalPlayer?.requestFullscreen) {
                  internalPlayer.requestFullscreen();
                }
              }
            }}
            className="text-white hover:text-blue-400 transition"
          >
            <FiMaximize2 size={18} />
          </button>
        </div>

        {/* Video Title */}
        {title && (
          <div className="mt-3 text-white text-sm font-medium">
            {title}
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoPlayer;