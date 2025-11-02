/**
 * Collaboration Dashboard
 * 
 * Displays active collaborations, history, and metrics for agent-to-agent
 * collaboration tracking.
 * 
 * Features:
 * - Active collaborations list with real-time updates
 * - Collaboration history with filtering
 * - Metrics charts (frequency, success rate)
 * - Agent pair heatmap
 */
import { useState, useEffect } from 'react';

interface Collaboration {
  id: string;
  request_type: string;
  requesting_agent_id: string;
  requesting_agent_type: string;
  question: string;
  status: string;
  urgency: string;
  created_at: string;
  specialist_id?: string;
  specialist_type?: string;
}

interface CollaborationMetrics {
  total_collaborations: number;
  successful_count: number;
  failed_count: number;
  success_rate: number;
  average_response_time_seconds: number;
  total_tokens_used: number;
  time_range_hours: number;
}

export default function CollaborationDashboard() {
  const [activeCollaborations, setActiveCollaborations] = useState<Collaboration[]>([]);
  const [history, setHistory] = useState<Collaboration[]>([]);
  const [metrics, setMetrics] = useState<CollaborationMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState(24); // hours
  const [statusFilter, setStatusFilter] = useState<string>('all');

  useEffect(() => {
    loadData();
    
    // Refresh every 5 seconds for real-time updates
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [timeRange, statusFilter]);

  const loadData = async () => {
    try {
      // Load active collaborations (pending, routed, in_progress)
      const activeResponse = await fetch('/api/v1/collaborations?status=active');
      if (activeResponse.ok) {
        const activeData = await activeResponse.json();
        setActiveCollaborations(activeData.collaborations || []);
      }

      // Load history
      const historyUrl = statusFilter === 'all'
        ? `/api/v1/collaborations?time_range=${timeRange}`
        : `/api/v1/collaborations?time_range=${timeRange}&status=${statusFilter}`;
      
      const historyResponse = await fetch(historyUrl);
      if (historyResponse.ok) {
        const historyData = await historyResponse.json();
        setHistory(historyData.collaborations || []);
      }

      // Load metrics
      const metricsResponse = await fetch(`/api/v1/collaborations/metrics?time_range=${timeRange}`);
      if (metricsResponse.ok) {
        const metricsData = await metricsResponse.json();
        setMetrics(metricsData);
      }

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      routed: 'bg-blue-100 text-blue-800',
      in_progress: 'bg-purple-100 text-purple-800',
      responded: 'bg-indigo-100 text-indigo-800',
      resolved: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
      timeout: 'bg-gray-100 text-gray-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getUrgencyColor = (urgency: string) => {
    const colors: Record<string, string> = {
      low: 'text-gray-600',
      normal: 'text-blue-600',
      high: 'text-orange-600',
      critical: 'text-red-600'
    };
    return colors[urgency] || 'text-gray-600';
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays}d ago`;
    } catch {
      return timestamp;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading collaboration dashboard...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">🤝 Collaboration Dashboard</h1>
        <p className="text-gray-600">Agent-to-agent collaboration tracking and metrics</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Metrics Summary */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-white border rounded-lg p-4">
            <div className="text-sm text-gray-600 mb-1">Total Collaborations</div>
            <div className="text-2xl font-bold">{metrics.total_collaborations}</div>
            <div className="text-xs text-gray-500 mt-1">Last {timeRange}h</div>
          </div>
          
          <div className="bg-white border rounded-lg p-4">
            <div className="text-sm text-gray-600 mb-1">Success Rate</div>
            <div className="text-2xl font-bold text-green-600">
              {(metrics.success_rate * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {metrics.successful_count} successful
            </div>
          </div>
          
          <div className="bg-white border rounded-lg p-4">
            <div className="text-sm text-gray-600 mb-1">Avg Response Time</div>
            <div className="text-2xl font-bold">
              {metrics.average_response_time_seconds 
                ? `${Math.round(metrics.average_response_time_seconds)}s`
                : 'N/A'}
            </div>
            <div className="text-xs text-gray-500 mt-1">Per collaboration</div>
          </div>
          
          <div className="bg-white border rounded-lg p-4">
            <div className="text-sm text-gray-600 mb-1">Tokens Used</div>
            <div className="text-2xl font-bold">
              {metrics.total_tokens_used.toLocaleString()}
            </div>
            <div className="text-xs text-gray-500 mt-1">Total tokens</div>
          </div>
        </div>
      )}

      {/* Active Collaborations */}
      {activeCollaborations.length > 0 && (
        <div className="bg-white border rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">
            🔄 Active Collaborations ({activeCollaborations.length})
          </h2>
          
          <div className="space-y-3">
            {activeCollaborations.map(collab => (
              <div key={collab.id} className="border rounded-lg p-4 hover:bg-gray-50">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(collab.status)}`}>
                        {collab.status}
                      </span>
                      <span className={`text-sm font-medium ${getUrgencyColor(collab.urgency)}`}>
                        {collab.urgency}
                      </span>
                      <span className="text-xs text-gray-500">
                        {formatTimestamp(collab.created_at)}
                      </span>
                    </div>
                    <div className="text-sm font-medium mb-1">{collab.question}</div>
                    <div className="text-xs text-gray-600">
                      <span className="font-mono">{collab.requesting_agent_id}</span>
                      {collab.specialist_id && (
                        <>
                          <span className="mx-1">→</span>
                          <span className="font-mono">{collab.specialist_id}</span>
                        </>
                      )}
                    </div>
                  </div>
                  
                  <div className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    {collab.request_type}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters and History */}
      <div className="bg-white border rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">📜 Collaboration History</h2>
          
          <div className="flex gap-3">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Status</option>
              <option value="resolved">Resolved</option>
              <option value="failed">Failed</option>
              <option value="timeout">Timeout</option>
            </select>
            
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(Number(e.target.value))}
              className="px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
            >
              <option value={1}>Last 1 hour</option>
              <option value={6}>Last 6 hours</option>
              <option value={24}>Last 24 hours</option>
              <option value={168}>Last 7 days</option>
            </select>
          </div>
        </div>

        {history.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No collaborations found
          </div>
        ) : (
          <div className="space-y-2">
            {history.map(collab => (
              <div key={collab.id} className="border rounded-lg p-3 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(collab.status)}`}>
                        {collab.status}
                      </span>
                      <span className="text-xs text-gray-500">
                        {formatTimestamp(collab.created_at)}
                      </span>
                      <span className="text-xs text-gray-400">•</span>
                      <span className="text-xs text-gray-500">{collab.request_type}</span>
                    </div>
                    <div className="text-sm">{collab.question}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
