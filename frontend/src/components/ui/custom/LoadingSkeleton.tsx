import React from 'react';

interface LoadingSkeletonProps {
  className?: string;
  rows?: number;
}

/**
 * Card skeleton loader for consistent loading states
 */
export const CardSkeleton: React.FC<LoadingSkeletonProps> = ({
  className = ''
}) => (
  <div className={`bg-white rounded-lg shadow p-6 animate-pulse ${className}`}>
    <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
    <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
    <div className="h-4 bg-gray-200 rounded w-full"></div>
  </div>
);

/**
 * Table row skeleton loader
 */
export const TableRowSkeleton: React.FC<LoadingSkeletonProps> = ({
  rows = 5
}) => (
  <>
    {Array.from({ length: rows }).map((_, i) => (
      <tr key={i} className="animate-pulse">
        <td className="px-6 py-4">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
        </td>
        <td className="px-6 py-4">
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </td>
        <td className="px-6 py-4">
          <div className="h-4 bg-gray-200 rounded w-1/4"></div>
        </td>
      </tr>
    ))}
  </>
);

/**
 * List skeleton loader
 */
export const ListSkeleton: React.FC<LoadingSkeletonProps> = ({
  rows = 5,
  className = ''
}) => (
  <div className={`space-y-3 ${className}`}>
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="flex items-center space-x-4 animate-pulse">
        <div className="h-12 w-12 bg-gray-200 rounded-full"></div>
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-3 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    ))}
  </div>
);

/**
 * Page skeleton loader for full page loading states
 */
export const PageSkeleton: React.FC = () => (
  <div className="min-h-screen bg-gray-50 animate-pulse">
    {/* Header */}
    <div className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <div className="h-8 w-32 bg-gray-200 rounded"></div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="h-8 w-8 bg-gray-200 rounded-full"></div>
          </div>
        </div>
      </div>
    </div>

    {/* Content */}
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="h-8 w-1/3 bg-gray-200 rounded mb-6"></div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <CardSkeleton />
        <CardSkeleton />
        <CardSkeleton />
      </div>
      <div className="bg-white rounded-lg shadow">
        <div className="h-16 bg-gray-200 rounded-t-lg"></div>
        <div className="p-6 space-y-4">
          <div className="h-4 bg-gray-200 rounded w-full"></div>
          <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          <div className="h-4 bg-gray-200 rounded w-4/6"></div>
        </div>
      </div>
    </main>
  </div>
);

/**
 * Chart skeleton loader
 */
export const ChartSkeleton: React.FC<{ className?: string }> = ({
  className = ''
}) => (
  <div className={`bg-white rounded-lg shadow p-6 animate-pulse ${className}`}>
    <div className="h-6 bg-gray-200 rounded w-1/3 mb-6"></div>
    <div className="h-64 bg-gray-100 rounded flex items-end justify-around p-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="w-12 bg-gray-200 rounded-t"
          style={{ height: `${Math.random() * 60 + 20}%` }}
        ></div>
      ))}
    </div>
  </div>
);

export default {
  Card: CardSkeleton,
  TableRow: TableRowSkeleton,
  List: ListSkeleton,
  Page: PageSkeleton,
  Chart: ChartSkeleton,
};
