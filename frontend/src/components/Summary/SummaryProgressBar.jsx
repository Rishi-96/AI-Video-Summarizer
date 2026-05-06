import React from 'react';
import { FiCpu, FiMic, FiFileText, FiVideo, FiCheck, FiAlertCircle } from 'react-icons/fi';

/**
 * SummaryProgressBar — Real-time progress display powered by SSE.
 * Shows a smooth animated progress bar with step descriptions and icons.
 */
const stepIcons = {
  'queued':                   <FiCpu />,
  'starting':                 <FiCpu />,
  'transcribing audio':       <FiMic />,
  'transcription complete':   <FiMic />,
  'analyzing content (parallel)': <FiCpu />,
  'analysis complete':        <FiFileText />,
  'generating summary':       <FiFileText />,
  'summary complete':         <FiFileText />,
  'key points extracted':     <FiFileText />,
  'generating subtitles':     <FiFileText />,
  'generating summary video': <FiVideo />,
  'saving to database':       <FiCheck />,
  'complete':                 <FiCheck />,
  'failed':                   <FiAlertCircle />,
};

const SummaryProgressBar = ({ progress = 0, step = '', status = '' }) => {
  if (!status || status === 'done') return null;

  const isFailed = status === 'failed';
  const displayStep = step
    ? step.charAt(0).toUpperCase() + step.slice(1)
    : status?.charAt(0).toUpperCase() + status?.slice(1);

  const icon = stepIcons[step] || stepIcons[status] || <FiCpu />;
  const barColor = isFailed
    ? 'bg-red-500'
    : progress > 80
      ? 'bg-green-500'
      : progress > 50
        ? 'bg-blue-500'
        : 'bg-indigo-500';

  return (
    <div className="w-full bg-gray-800/50 border border-gray-700 rounded-xl p-5 backdrop-blur-sm">
      {/* Step info */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-200">
          <span className="text-blue-400 animate-pulse">{icon}</span>
          <span>{displayStep}</span>
        </div>
        <span className="text-sm font-mono text-gray-400">{Math.round(progress)}%</span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-700 rounded-full h-2.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${barColor}`}
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>

      {/* Stage indicators */}
      <div className="flex justify-between mt-2 text-xs text-gray-500">
        <span className={progress >= 10 ? 'text-blue-400' : ''}>Transcribe</span>
        <span className={progress >= 40 ? 'text-blue-400' : ''}>Analyze</span>
        <span className={progress >= 65 ? 'text-blue-400' : ''}>Subtitles</span>
        <span className={progress >= 70 ? 'text-blue-400' : ''}>Video</span>
        <span className={progress >= 100 ? 'text-green-400' : ''}>Done</span>
      </div>
    </div>
  );
};

export default SummaryProgressBar;
