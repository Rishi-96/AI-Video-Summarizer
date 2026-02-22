import React from 'react';
import { FiFileText, FiList, FiCpu, FiClock } from 'react-icons/fi';

const SummaryDisplay = ({ summary }) => {
  if (!summary) {
    return (
      <div className="bg-gray-800 rounded-xl p-8 text-center">
        <FiFileText className="mx-auto h-12 w-12 text-gray-600" />
        <p className="mt-4 text-gray-400">No summary available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Text */}
      <div className="bg-gray-800 rounded-xl p-6">
        <div className="flex items-center mb-4">
          <FiFileText className="h-5 w-5 text-blue-500 mr-2" />
          <h3 className="text-lg font-medium text-white">Summary</h3>
        </div>
        <p className="text-gray-300 leading-relaxed">
          {summary.text_summary}
        </p>
      </div>

      {/* Key Points */}
      {summary.key_points && summary.key_points.length > 0 && (
        <div className="bg-gray-800 rounded-xl p-6">
          <div className="flex items-center mb-4">
            <FiList className="h-5 w-5 text-green-500 mr-2" />
            <h3 className="text-lg font-medium text-white">Key Points</h3>
          </div>
          <ul className="space-y-2">
            {summary.key_points.map((point, index) => (
              <li key={index} className="flex items-start">
                <span className="inline-block w-5 h-5 bg-green-500/20 text-green-400 rounded-full text-xs flex items-center justify-center mr-2 mt-0.5">
                  {index + 1}
                </span>
                <span className="text-gray-300">{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Transcript Preview */}
      {summary.transcript && (
        <div className="bg-gray-800 rounded-xl p-6">
          <div className="flex items-center mb-4">
            <FiCpu className="h-5 w-5 text-purple-500 mr-2" />
            <h3 className="text-lg font-medium text-white">Transcript Preview</h3>
          </div>
          <p className="text-gray-400 text-sm italic">
            "{summary.transcript}"
          </p>
        </div>
      )}

      {/* Metadata */}
      <div className="bg-gray-800/50 rounded-xl p-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Language:</span>
            <span className="ml-2 text-gray-300">{summary.language || 'en'}</span>
          </div>
          <div>
            <span className="text-gray-500">Created:</span>
            <span className="ml-2 text-gray-300">
              {new Date(summary.created_at).toLocaleDateString()}
            </span>
          </div>
          <div>
            <span className="text-gray-500">Segments:</span>
            <span className="ml-2 text-gray-300">{summary.segments?.length || 0}</span>
          </div>
          <div>
            <span className="text-gray-500">Summary ID:</span>
            <span className="ml-2 text-gray-300 font-mono text-xs">
              {summary.summary_id?.substring(0, 8)}...
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SummaryDisplay;