/**
 * Prompt Version History Viewer
 * 
 * Displays all versions of prompts for an agent type with:
 * - Version list with active indicator
 * - Date, author, notes
 * - Click to view full prompt content
 * - Sortable and filterable
 */
import { useState, useEffect } from 'react';

interface PromptVersion {
  version: string;
  is_active: boolean;
  created_at: string | null;
  created_by: string | null;
  notes: string | null;
}

interface PromptHistoryProps {
  agentType: string;
  onVersionSelect?: (version: string) => void;
}

export default function PromptHistory({ agentType, onVersionSelect }: PromptHistoryProps) {
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    loadVersions();
  }, [agentType]);

  const loadVersions = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/prompts/${agentType}/versions`);
      if (!response.ok) throw new Error('Failed to load versions');
      const data = await response.json();
      setVersions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const sortedVersions = [...versions].sort((a, b) => {
    const compareResult = a.version.localeCompare(b.version, undefined, { numeric: true });
    return sortOrder === 'desc' ? -compareResult : compareResult;
  });

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return <div className="text-center py-4">Loading versions...</div>;
  }

  if (error) {
    return <div className="text-red-600 text-sm">Error: {error}</div>;
  }

  return (
    <div className="bg-white border rounded-lg shadow">
      {/* Header */}
      <div className="px-4 py-3 border-b bg-gray-50">
        <div className="flex justify-between items-center">
          <h3 className="font-semibold text-gray-900">
            Version History ({agentType})
          </h3>
          <button
            onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Sort: {sortOrder === 'desc' ? 'Newest First' : 'Oldest First'}
          </button>
        </div>
      </div>

      {/* Version List */}
      <div className="divide-y">
        {sortedVersions.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-500">
            No versions found for {agentType}
          </div>
        ) : (
          sortedVersions.map((version) => (
            <div
              key={version.version}
              className={`px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors ${
                version.is_active ? 'bg-blue-50' : ''
              }`}
              onClick={() => onVersionSelect?.(version.version)}
            >
              <div className="flex items-start justify-between">
                {/* Version Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-gray-900">
                      v{version.version}
                    </span>
                    {version.is_active && (
                      <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded">
                        Active
                      </span>
                    )}
                  </div>
                  
                  {version.notes && (
                    <p className="text-sm text-gray-600 mt-1">{version.notes}</p>
                  )}
                  
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                    <span>📅 {formatDate(version.created_at)}</span>
                    {version.created_by && (
                      <span>👤 {version.created_by}</span>
                    )}
                  </div>
                </div>

                {/* View Arrow */}
                <div className="ml-4 text-gray-400">
                  →
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t bg-gray-50 text-xs text-gray-500">
        {versions.length} version{versions.length !== 1 ? 's' : ''} total
        {' • '}
        Active version: v{versions.find(v => v.is_active)?.version || 'None'}
      </div>
    </div>
  );
}
