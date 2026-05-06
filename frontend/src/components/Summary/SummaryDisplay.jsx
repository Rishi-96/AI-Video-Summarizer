import React, { useState } from 'react';
import { FiFileText, FiList, FiCpu, FiDownload, FiVolume2, FiEdit3, FiLoader, FiCopy, FiCheck, FiImage, FiZap, FiGlobe } from 'react-icons/fi';
import { summariesAPI } from '../../services/api';
import toast from 'react-hot-toast';

const SummaryDisplay = ({ summary }) => {
  const [ttsLoading, setTtsLoading] = useState(false);
  const [ttsAudioUrl, setTtsAudioUrl] = useState(null);
  const [descLoading, setDescLoading] = useState(false);
  const [descriptions, setDescriptions] = useState(null);
  const [copiedField, setCopiedField] = useState(null);
  const [thumbLoading, setThumbLoading] = useState(false);
  const [thumbnailUrl, setThumbnailUrl] = useState(null);
  const [highlightLoading, setHighlightLoading] = useState(false);
  const [highlights, setHighlights] = useState(null);
  const [translateLoading, setTranslateLoading] = useState(false);
  const [translation, setTranslation] = useState(null);
  const [targetLang, setTargetLang] = useState('es');

  if (!summary) {
    return (
      <div className="bg-gray-800 rounded-xl p-8 text-center">
        <FiFileText className="mx-auto h-12 w-12 text-gray-600" />
        <p className="mt-4 text-gray-400">No summary available</p>
      </div>
    );
  }

  // ── Subtitle download ─────────────────────────────────────────────
  const handleDownloadSubtitle = async (format) => {
    try {
      const response = await summariesAPI.downloadSubtitles(summary.summary_id, format);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `subtitles-${summary.summary_id.substring(0, 8)}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} subtitles downloaded!`);
    } catch (err) {
      console.error('Subtitle download failed:', err);
      toast.error(`Failed to download ${format.toUpperCase()} subtitles`);
    }
  };

  // ── TTS generation ────────────────────────────────────────────────
  const handleGenerateTTS = async () => {
    setTtsLoading(true);
    try {
      const response = await summariesAPI.generateTTS(summary.summary_id);
      const audioUrl = response.data.audio_url;
      // Build absolute URL for the audio player
      const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      setTtsAudioUrl(`${baseUrl}${audioUrl}`);
      toast.success('Audio generated! Press play to listen.');
    } catch (err) {
      console.error('TTS failed:', err);
      toast.error('Failed to generate audio');
    } finally {
      setTtsLoading(false);
    }
  };

  // ── Description generation ────────────────────────────────────────
  const handleGenerateDescriptions = async () => {
    setDescLoading(true);
    try {
      const response = await summariesAPI.generateDescriptions(summary.summary_id);
      setDescriptions(response.data.descriptions);
      toast.success('Descriptions generated!');
    } catch (err) {
      console.error('Description generation failed:', err);
      toast.error('Failed to generate descriptions');
    } finally {
      setDescLoading(false);
    }
  };

  // ── Copy to clipboard ─────────────────────────────────────────────
  const copyToClipboard = (text, field) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    toast.success('Copied to clipboard!');
    setTimeout(() => setCopiedField(null), 2000);
  };

  // ── Thumbnail generation ──────────────────────────────────────────
  const handleGenerateThumbnail = async () => {
    setThumbLoading(true);
    try {
      await summariesAPI.generateThumbnail(summary.summary_id);
      setThumbnailUrl(summariesAPI.getThumbnailUrl(summary.summary_id));
      toast.success('Thumbnail generated!');
    } catch (err) {
      console.error('Thumbnail failed:', err);
      toast.error('Failed to generate thumbnail');
    } finally {
      setThumbLoading(false);
    }
  };

  // ── Highlight detection ───────────────────────────────────────────
  const handleDetectHighlights = async () => {
    setHighlightLoading(true);
    try {
      const response = await summariesAPI.detectHighlights(summary.summary_id);
      setHighlights(response.data.highlights);
      toast.success(`Found ${response.data.highlights.length} highlights!`);
    } catch (err) {
      console.error('Highlight detection failed:', err);
      toast.error('Failed to detect highlights');
    } finally {
      setHighlightLoading(false);
    }
  };

  // ── Translation ────────────────────────────────────────────────────
  const handleTranslate = async () => {
    setTranslateLoading(true);
    try {
      const response = await summariesAPI.translateSummary(summary.summary_id, targetLang);
      setTranslation(response.data);
      toast.success(`Translated to ${targetLang.toUpperCase()}!`);
    } catch (err) {
      console.error('Translation failed:', err);
      toast.error('Failed to translate');
    } finally {
      setTranslateLoading(false);
    }
  };

  const LANG_OPTIONS = [
    ['es', 'Spanish'], ['fr', 'French'], ['de', 'German'], ['it', 'Italian'],
    ['pt', 'Portuguese'], ['ja', 'Japanese'], ['ko', 'Korean'], ['zh', 'Chinese'],
    ['ar', 'Arabic'], ['hi', 'Hindi'], ['ru', 'Russian'], ['tr', 'Turkish'],
    ['nl', 'Dutch'], ['sv', 'Swedish'], ['pl', 'Polish'], ['vi', 'Vietnamese'],
  ];

  return (
    <div className="space-y-6">
      {/* Summary Text */}
      <div className="bg-gray-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center">
            <FiFileText className="h-5 w-5 text-blue-500 mr-2" />
            <h3 className="text-lg font-medium text-white">Summary</h3>
          </div>
          <button
            onClick={() => copyToClipboard(summary.text_summary, 'summary')}
            className="text-gray-400 hover:text-white transition p-1.5 rounded-lg hover:bg-gray-700"
            title="Copy summary"
          >
            {copiedField === 'summary' ? <FiCheck className="text-green-400" /> : <FiCopy />}
          </button>
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
                <span className="inline-flex w-5 h-5 bg-green-500/20 text-green-400 rounded-full text-xs items-center justify-center mr-2 mt-0.5 flex-shrink-0">
                  {index + 1}
                </span>
                <span className="text-gray-300">{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Phase 2: Action Buttons ─────────────────────────────────── */}
      <div className="bg-gray-800 rounded-xl p-6">
        <h3 className="text-lg font-medium text-white mb-4">Export & Tools</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {/* Subtitle Downloads */}
          <button
            onClick={() => handleDownloadSubtitle('srt')}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600/20 text-indigo-400 rounded-lg hover:bg-indigo-600/30 transition text-sm font-medium"
          >
            <FiDownload className="h-4 w-4" />
            SRT Subtitles
          </button>
          <button
            onClick={() => handleDownloadSubtitle('vtt')}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-purple-600/20 text-purple-400 rounded-lg hover:bg-purple-600/30 transition text-sm font-medium"
          >
            <FiDownload className="h-4 w-4" />
            VTT Subtitles
          </button>

          {/* TTS */}
          <button
            onClick={handleGenerateTTS}
            disabled={ttsLoading}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-600/20 text-amber-400 rounded-lg hover:bg-amber-600/30 transition text-sm font-medium disabled:opacity-50"
          >
            {ttsLoading ? <FiLoader className="h-4 w-4 animate-spin" /> : <FiVolume2 className="h-4 w-4" />}
            {ttsLoading ? 'Generating...' : 'Listen'}
          </button>

          {/* Descriptions */}
          <button
            onClick={handleGenerateDescriptions}
            disabled={descLoading}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-600/20 text-teal-400 rounded-lg hover:bg-teal-600/30 transition text-sm font-medium disabled:opacity-50"
          >
            {descLoading ? <FiLoader className="h-4 w-4 animate-spin" /> : <FiEdit3 className="h-4 w-4" />}
            {descLoading ? 'Generating...' : 'Descriptions'}
          </button>

          {/* Thumbnail */}
          <button
            onClick={handleGenerateThumbnail}
            disabled={thumbLoading}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-rose-600/20 text-rose-400 rounded-lg hover:bg-rose-600/30 transition text-sm font-medium disabled:opacity-50"
          >
            {thumbLoading ? <FiLoader className="h-4 w-4 animate-spin" /> : <FiImage className="h-4 w-4" />}
            {thumbLoading ? 'Generating...' : 'Thumbnail'}
          </button>

          {/* Highlights */}
          <button
            onClick={handleDetectHighlights}
            disabled={highlightLoading}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-yellow-600/20 text-yellow-400 rounded-lg hover:bg-yellow-600/30 transition text-sm font-medium disabled:opacity-50"
          >
            {highlightLoading ? <FiLoader className="h-4 w-4 animate-spin" /> : <FiZap className="h-4 w-4" />}
            {highlightLoading ? 'Detecting...' : 'Highlights'}
          </button>
        </div>

        {/* Translation row */}
        <div className="flex items-center gap-2 mt-3">
          <FiGlobe className="h-4 w-4 text-cyan-400" />
          <select
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
            className="bg-gray-700 text-gray-300 text-sm rounded-lg px-3 py-2 border border-gray-600 focus:border-cyan-500 focus:outline-none"
          >
            {LANG_OPTIONS.map(([code, name]) => (
              <option key={code} value={code}>{name}</option>
            ))}
          </select>
          <button
            onClick={handleTranslate}
            disabled={translateLoading}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-600/20 text-cyan-400 rounded-lg hover:bg-cyan-600/30 transition text-sm font-medium disabled:opacity-50"
          >
            {translateLoading ? <FiLoader className="h-4 w-4 animate-spin" /> : <FiGlobe className="h-4 w-4" />}
            {translateLoading ? 'Translating...' : 'Translate'}
          </button>
        </div>

        {/* Translation Result */}
        {translation && (
          <div className="mt-4 p-4 bg-cyan-900/20 border border-cyan-700/30 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
                Translated Summary ({translation.target_lang?.toUpperCase()})
              </span>
              <button
                onClick={() => copyToClipboard(translation.translated_summary, 'translation')}
                className="text-gray-400 hover:text-white transition p-1"
              >
                {copiedField === 'translation' ? <FiCheck className="text-green-400 h-3.5 w-3.5" /> : <FiCopy className="h-3.5 w-3.5" />}
              </button>
            </div>
            <p className="text-gray-300 text-sm leading-relaxed">{translation.translated_summary}</p>
            {translation.translated_key_points?.length > 0 && (
              <div className="mt-3">
                <p className="text-xs text-cyan-400 mb-1">Key Points:</p>
                <ul className="space-y-1">
                  {translation.translated_key_points.map((pt, i) => (
                    <li key={i} className="text-gray-300 text-sm flex items-start gap-2">
                      <span className="text-cyan-500">•</span> {pt}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* TTS Audio Player */}
        {ttsAudioUrl && (
          <div className="mt-4 p-3 bg-gray-700/50 rounded-lg">
            <p className="text-xs text-gray-400 mb-2">Summary Audio (Microsoft Edge TTS)</p>
            <audio controls src={ttsAudioUrl} className="w-full" />
          </div>
        )}

        {/* Generated Descriptions */}
        {descriptions && (
          <div className="mt-4 space-y-3">
            {Object.entries(descriptions).map(([type, desc]) => (
              <div key={type} className="p-3 bg-gray-700/50 rounded-lg">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold uppercase tracking-wider text-blue-400">
                    {type === 'oneliner' ? 'One-Liner' : type === 'seo' ? 'SEO Optimized' : type.charAt(0).toUpperCase() + type.slice(1)}
                  </span>
                  <button
                    onClick={() => copyToClipboard(desc.content, type)}
                    className="text-gray-400 hover:text-white transition p-1"
                    title="Copy"
                  >
                    {copiedField === type ? <FiCheck className="text-green-400 h-3.5 w-3.5" /> : <FiCopy className="h-3.5 w-3.5" />}
                  </button>
                </div>
                <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap">
                  {desc.content}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Thumbnail Preview */}
      {thumbnailUrl && (
        <div className="bg-gray-800 rounded-xl p-6">
          <div className="flex items-center mb-4">
            <FiImage className="h-5 w-5 text-rose-500 mr-2" />
            <h3 className="text-lg font-medium text-white">AI Thumbnail</h3>
          </div>
          <img
            src={thumbnailUrl}
            alt="Generated thumbnail"
            className="w-full rounded-lg shadow-lg border border-gray-700"
          />
          <a
            href={thumbnailUrl}
            download
            className="inline-flex items-center gap-2 mt-3 text-sm text-rose-400 hover:text-rose-300 transition"
          >
            <FiDownload className="h-4 w-4" /> Download Thumbnail
          </a>
        </div>
      )}

      {/* Highlights Panel */}
      {highlights && highlights.length > 0 && (
        <div className="bg-gray-800 rounded-xl p-6">
          <div className="flex items-center mb-4">
            <FiZap className="h-5 w-5 text-yellow-500 mr-2" />
            <h3 className="text-lg font-medium text-white">Top Highlights</h3>
          </div>
          <div className="space-y-2">
            {highlights.slice(0, 8).map((hl, idx) => {
              const start = hl.start || 0;
              const mins = Math.floor(start / 60);
              const secs = Math.floor(start % 60);
              const score = (hl.highlight_score * 100).toFixed(0);
              return (
                <div key={idx} className="flex items-start gap-3 p-3 bg-gray-700/40 rounded-lg">
                  <span className="flex-shrink-0 text-xs font-mono text-yellow-400 bg-yellow-500/10 px-2 py-1 rounded">
                    {mins}:{secs.toString().padStart(2, '0')}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-300 text-sm truncate">{hl.text}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex-1 bg-gray-600 rounded-full h-1.5">
                        <div
                          className="bg-yellow-500 h-1.5 rounded-full transition-all"
                          style={{ width: `${score}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500">{score}%</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
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