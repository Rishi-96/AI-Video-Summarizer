import React from 'react';
import { motion } from 'framer-motion';
import { FiVideo, FiUploadCloud } from 'react-icons/fi';
import { Link } from 'react-router-dom';

const EmptyState = ({ title, subtitle, actionText, actionLink }) => {
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
            className="glass-card p-12 flex flex-col items-center justify-center text-center mx-auto max-w-2xl mt-8"
        >
            <div className="relative mb-6">
                <div className="absolute inset-0 bg-blue-500 blur-[40px] opacity-20 rounded-full"></div>
                <div className="relative bg-gray-800 border border-gray-700 w-24 h-24 rounded-2xl flex items-center justify-center shadow-2xl">
                    <FiVideo className="w-10 h-10 text-blue-400" />
                </div>
            </div>

            <h3 className="text-2xl font-bold text-white mb-3">{title || 'No Videos Yet'}</h3>
            <p className="text-gray-400 mb-8 max-w-md">
                {subtitle || 'Upload your first video to generate AI-powered summaries and insights automatically.'}
            </p>

            <Link to={actionLink || '/upload'}>
                <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-medium shadow-lg shadow-blue-500/30 transition-colors"
                >
                    <FiUploadCloud className="w-5 h-5" />
                    {actionText || 'Upload Video'}
                </motion.button>
            </Link>
        </motion.div>
    );
};

export default EmptyState;
