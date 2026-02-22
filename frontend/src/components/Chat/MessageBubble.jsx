import React from 'react';
import { FiCpu, FiUser, FiAlertCircle } from 'react-icons/fi';
import { formatDistanceToNow } from 'date-fns';

const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user';
  const isError = message.isError;

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 ${isUser ? 'ml-3' : 'mr-3'}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
            isUser ? 'bg-blue-600' : isError ? 'bg-red-600' : 'bg-purple-600'
          }`}>
            {isUser ? (
              <FiUser className="h-4 w-4 text-white" />
            ) : isError ? (
              <FiAlertCircle className="h-4 w-4 text-white" />
            ) : (
              <FiCpu className="h-4 w-4 text-white" />
            )}
          </div>
        </div>

        {/* Message Content */}
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          <div
            className={`rounded-2xl px-4 py-2 ${
              isUser
                ? 'bg-blue-600 text-white'
                : isError
                ? 'bg-red-600/20 text-red-400'
                : 'bg-gray-700 text-gray-200'
            }`}
          >
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          </div>
          
          {/* Timestamp */}
          {message.timestamp && (
            <span className="text-xs text-gray-500 mt-1">
              {formatDistanceToNow(new Date(message.timestamp), { addSuffix: true })}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;