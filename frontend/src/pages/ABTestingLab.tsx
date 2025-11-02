/**
 * A/B Testing Lab
 * 
 * Compare two prompt versions side-by-side and optionally test them.
 * Features:
 * - Select agent type
 * - Choose two versions to compare
 * - View side-by-side comparison
 * - Promote winning version
 */
import { useState, useEffect } from 'react';
import PromptComparison from '../components/PromptComparison';

const BUILT_IN_AGENTS = [
  'orchestrator',
  'backend_dev',
  'frontend_dev',
  'qa_engineer',
  'security_expert',
  'devops_engineer',
  'documentation_expert',
  'uiux_designer',
  'github_specialist',
  'workshopper',
  'project_manager',
];

interface Version {
  version: string;
  is_active: boolean;
  created_at: string | null;
}

export default function ABTestingLab() {
  const [selectedAgent, setSelectedAgent] = useState('backend_dev');
  const [versions, setVersions] = useState<Version[]>([]);
  const [versionA, setVersionA] = useState('');
  const [versionB, setVersionB] = useState('');
  const [loading, setLoading] = useState(false);
  const [promoting, setPromoting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showComparison, setShowComparison] = useState(false);

  useEffect(() => {
    loadVersions();
  }, [selectedAgent]);

  const loadVersions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`/api/v1/prompts/${selectedAgent}/versions`);
      if (!response.ok) throw new Error('Failed to load versions');
      const data = await response.json();
      setVersions(data);

      // Auto-select first two versions
      if (data.length >= 2) {
        setVersionA(data[0].version);
        setVersionB(data[1].version);
      } else if (data.length === 1) {
        setVersionA(data[0].version);
        setVersionB('');
      } else {
        setVersionA('');
        setVersionB('');
      }

      setShowComparison(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load versions');
    } finally {
      setLoading(false);
    }
  };

  const promoteVersion = async (version: string) => {
    try {
      setPromoting(true);
      setError(null);
      setSuccess(null);

      const response = await fetch('/api/v1/prompts/promote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_type: selectedAgent,
          version: version
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to promote version');
      }

      setSuccess(`Version ${version} promoted to active!`);
      
      // Reload versions
      setTimeout(() => {
        setSuccess(null);
        loadVersions();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to promote');
    } finally {
      setPromoting(false);
    }
  };

  const canCompare = versionA && versionB && versionA !== versionB;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">A/B Testing Lab</h1>
          <p className="text-gray-600 mt-1">
            Compare prompt versions side-by-side and promote the winner
          </p>
        </div>

        {/* Controls */}
        <div className="bg-white border rounded-lg shadow p-6 mb-6">
          <div className="grid grid-cols-3 gap-4">
            {/* Agent Selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Agent Type
              </label>
              <select
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
                className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
              >
                {BUILT_IN_AGENTS.map(agent => (
                  <option key={agent} value={agent}>
                    {agent.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
              <div className="mt-1 text-xs text-gray-500">
                {versions.length} version{versions.length !== 1 ? 's' : ''} available
              </div>
            </div>

            {/* Version A Selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Version A
              </label>
              <select
                value={versionA}
                onChange={(e) => setVersionA(e.target.value)}
                disabled={loading || versions.length === 0}
                className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                <option value="">Select version...</option>
                {versions.map(v => (
                  <option key={v.version} value={v.version}>
                    v{v.version} {v.is_active ? '(Active)' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Version B Selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Version B
              </label>
              <select
                value={versionB}
                onChange={(e) => setVersionB(e.target.value)}
                disabled={loading || versions.length === 0}
                className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                <option value="">Select version...</option>
                {versions.map(v => (
                  <option key={v.version} value={v.version}>
                    v{v.version} {v.is_active ? '(Active)' : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Compare Button */}
          <div className="mt-4 flex items-center justify-between">
            <button
              onClick={() => setShowComparison(true)}
              disabled={!canCompare || loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Loading...' : 'Compare Versions'}
            </button>

            {versionA === versionB && versionA && (
              <span className="text-sm text-red-600">
                ⚠️ Please select two different versions
              </span>
            )}
          </div>

          {/* Status Messages */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {error}
            </div>
          )}

          {success && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded text-green-700 text-sm">
              {success}
            </div>
          )}
        </div>

        {/* Comparison View */}
        {showComparison && canCompare && (
          <div>
            {promoting && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-blue-700 text-sm">
                Promoting version...
              </div>
            )}
            <PromptComparison
              agentType={selectedAgent}
              versionA={versionA}
              versionB={versionB}
              onPromote={promoteVersion}
            />
          </div>
        )}

        {/* Empty State */}
        {versions.length === 0 && !loading && (
          <div className="bg-white border rounded-lg shadow p-12 text-center">
            <div className="text-6xl mb-4">🔬</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              No Versions Found
            </h3>
            <p className="text-gray-600 mb-4">
              No prompt versions exist for {selectedAgent}. Create versions in the Prompt Editor first.
            </p>
            <a
              href="/prompt-editor"
              className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Go to Prompt Editor
            </a>
          </div>
        )}

        {/* Instructions */}
        {!showComparison && versions.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="font-semibold text-blue-900 mb-2">How to use A/B Testing Lab</h3>
            <ol className="list-decimal list-inside space-y-1 text-sm text-blue-800">
              <li>Select an agent type from the dropdown</li>
              <li>Choose two different versions to compare (A and B)</li>
              <li>Click "Compare Versions" to see the differences</li>
              <li>Review the side-by-side comparison with diff highlighting</li>
              <li>Promote the better version to active if desired</li>
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}
