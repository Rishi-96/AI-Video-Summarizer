import React from 'react';
import { motion } from 'framer-motion';
import CountUp from 'react-countup';

const DashboardCard = ({ title, value, subtitle, icon: Icon, gradient, delay = 0, isNumber = true }) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay }}
            className={`relative overflow-hidden glass-card p-6 group cursor-default`}
        >
            {/* Background glow based on gradient */}
            <div className={`absolute -right-6 -top-6 w-32 h-32 rounded-full opacity-20 bg-gradient-to-br ${gradient} blur-2xl group-hover:opacity-40 transition-opacity duration-300`}></div>

            <div className="relative z-10">
                <div className="flex justify-between items-start">
                    <div>
                        <p className="text-gray-400 text-sm font-medium mb-1">{title}</p>
                        <h3 className="text-3xl font-bold text-white mb-2">
                            {isNumber && typeof value === 'number' ? (
                                <CountUp end={value} duration={2} separator="," />
                            ) : (
                                value
                            )}
                        </h3>
                        {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
                    </div>
                    <div className={`p-3 rounded-xl bg-gray-800/50 border border-gray-700/50 shadow-inner group-hover:scale-110 transition-transform duration-300`}>
                        <Icon className="w-6 h-6 text-gray-300 group-hover:text-white transition-colors duration-300" />
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

export default DashboardCard;
