import React, { useState, useRef, useEffect } from 'react';
import { FiSend, FiCpu, FiUser, FiLoader } from 'react-icons/fi';
import { chatAPI } from '../../services/api';
import MessageBubble from './MessageBubble';

const ChatInterface = ({ sessionId, summary }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    // Add initial greeting
    if (summary && messages.length === 0) {
      setMessages([
        {
          role: 'assistant',
          content: `Hello! I've analyzed your video summary. Ask me anything about "${summary.video_info?.filename || 'your video'}"!`,
          timestamp: new Date().toISOString()
        }
      ]);
    }
  }, [summary]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || loading) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    
    // Add user message to UI
    setMessages(prev => [
      ...prev,
      {
        role: 'user',
        content: userMessage,
        timestamp: new Date().toISOString()
      }
    ]);

    setLoading(true);

    try {
      const response = await chatAPI.askQuestion(sessionId, userMessage);
      
      // Add assistant response to UI
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: response.data.answer,
          timestamp: new Date().toISOString()
        }
      ]);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date().toISOString(),
          isError: true
        }
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-[600px] bg-gray-800 rounded-xl overflow-hidden">
      {/* Chat Header */}
      <div className="bg-gray-900 p-4 border-b border-gray-700">
        <div className="flex items-center">
          <FiCpu className="h-5 w-5 text-blue-500 mr-2" />
          <h3 className="text-white font-medium">AI Assistant</h3>
          {loading && (
            <span className="ml-2 flex items-center text-sm text-gray-400">
              <FiLoader className="animate-spin mr-1" />
              Thinking...
            </span>
          )}
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <MessageBubble key={index} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-700">
        <div className="flex items-center space-x-2">
          <input
            ref={inputRef}
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about the video..."
            disabled={loading}
            className="flex-1 bg-gray-700 text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || loading}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            <FiSend className="h-5 w-5" />
          </button>
        </div>
        <p className="mt-2 text-xs text-gray-500">
          Ask questions about the video content, summary, or key points
        </p>
      </div>
    </div>
  );
};

export default ChatInterface;