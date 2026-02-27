import React from 'react';

const SkeletonLoader = () => {
    return (
        <div className="space-y-8">
            {/* Cards Skeleton */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[1, 2, 3].map((i) => (
                    <div key={i} className="glass-card p-6 min-h-[140px] relative overflow-hidden">
                        <div className="skeleton-shimmer absolute inset-0"></div>
                        <div className="relative z-10 flex justify-between">
                            <div className="space-y-4 w-1/2">
                                <div className="h-4 bg-gray-700/50 rounded w-full"></div>
                                <div className="h-8 bg-gray-700/50 rounded w-3/4"></div>
                                <div className="h-3 bg-gray-700/50 rounded w-1/2"></div>
                            </div>
                            <div className="h-12 w-12 rounded-xl bg-gray-700/50"></div>
                        </div>
                    </div>
                ))}
            </div>

            {/* List Skeleton */}
            <div className="space-y-4 pt-4">
                <div className="h-8 bg-gray-700/50 rounded w-48 mb-6 relative overflow-hidden">
                    <div className="skeleton-shimmer absolute inset-0"></div>
                </div>
                {[1, 2, 3].map((i) => (
                    <div key={i} className="glass-card p-4 relative overflow-hidden">
                        <div className="skeleton-shimmer absolute inset-0"></div>
                        <div className="relative z-10 flex gap-4">
                            <div className="w-32 h-20 bg-gray-700/50 rounded-lg"></div>
                            <div className="flex-1 space-y-3">
                                <div className="h-5 bg-gray-700/50 rounded w-3/4"></div>
                                <div className="h-4 bg-gray-700/50 rounded w-1/2"></div>
                                <div className="h-3 bg-gray-700/50 rounded w-1/4 pt-2"></div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default SkeletonLoader;
