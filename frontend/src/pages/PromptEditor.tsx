/**
 * Prompt Editor
 * 
 * Edit and create new prompt versions for built-in agents.
 * Features:
 * - Text editor for prompt content
 * - Version metadata (notes)
 * - Save as new version or create patch
 * - Preview mode
 * - Version selector to load existing prompts
 */
import { useState, useEffect } from 'react';
import PromptHistory from '../components/PromptHistory';

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

export default function PromptEditor() {
  const [selectedAgent, setSelectedAgent] = useState('backend_dev');
  const [promptText, setPromptText] = useState('');
  const [version, setVersion] = useState('');
  const [notes, setNotes] = useState('');
  const [createdBy, setCreatedBy] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [previewMode, setPreviewMode] = useState(false);
  const [showHistory, setShowHistory] = useState(true);
  const [aiAssisting, setAiAssisting] = useState(false);
  const [assistRequest, setAssistRequest] = useState('');

  // Load active prompt when agent changes
  useEffect(() => {
    loadActivePrompt();
  }, [selectedAgent]);

  const loadActivePrompt = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/prompts/${selectedAgent}/active`);
      if (!response.ok) throw new Error('Failed to load active prompt');
      const data = await response.json();
      setPromptText(data.prompt_text);
      setVersion(data.version);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompt');
    } finally {
      setLoading(false);
    }
  };

  const loadSpecificVersion = async (versionStr: string) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/prompts/${selectedAgent}/${versionStr}`);
      if (!response.ok) throw new Error('Failed to load version');
      const data = await response.json();
      setPromptText(data.prompt_text);
      setVersion(versionStr);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load version');
    } finally {
      setLoading(false);
    }
  };

  const createNewVersion = async () => {
    if (!version || !promptText) {
      setError('Version and prompt text are required');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      const response = await fetch('/api/v1/prompts/versions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_type: selectedAgent,
          version: version,
          prompt_text: promptText,
          created_by: createdBy || 'user',
          notes: notes || undefined
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to create version');
      }

      setSuccess(`Version ${version} created successfully!`);
      setNotes('');
      
      // Reload to refresh history
      setTimeout(() => {
        setSuccess(null);
        loadActivePrompt();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const createPatch = async () => {
    if (!promptText) {
      setError('Prompt text is required');
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      const response = await fetch('/api/v1/prompts/patch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_type: selectedAgent,
          prompt_text: promptText,
          created_by: createdBy || 'user',
          notes: notes || 'Patch version'
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to create patch');
      }

      const data = await response.json();
      setSuccess(`Patch version ${data.version} created and activated!`);
      setNotes('');
      
      // Reload to refresh
      setTimeout(() => {
        setSuccess(null);
        loadActivePrompt();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create patch');
    } finally {
      setSaving(false);
    }
  };

  const getAiAssistance = async () => {
    if (!assistRequest) {
      setError('Please describe what you want help with');
      return;
    }

    try {
      setAiAssisting(true);
      setError(null);
      setSuccess(null);

      // Call the AI assist endpoint
      const context = promptText 
        ? `Agent type: ${selectedAgent}\nCurrent prompt (first 300 chars): ${promptText.substring(0, 300)}...`
        : `Agent type: ${selectedAgent}`;

      const response = await fetch('/api/v1/specialists/ai-assist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: assistRequest,
          context: context
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to get AI assistance' }));
        throw new Error(errorData.detail || 'Failed to get AI assistance');
      }

      const data = await response.json();
      
      // Append AI suggestion to current prompt
      setPromptText(prev => {
        if (prev) {
          return `${prev}\n\n--- AI Suggested Addition ---\n${data.suggestion}`;
        }
        return data.suggestion;
      });
      
      setSuccess('AI suggestions added! Review and edit as needed.');
      setAssistRequest('');
      
      // Clear success after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get AI assistance');
    } finally {
      setAiAssisting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Prompt Editor</h1>
          <p className="text-gray-600 mt-1">
            Edit and version control prompts for built-in agents
          </p>
        </div>

        <div className="grid grid-cols-12 gap-6">
          {/* Left Sidebar - Agent Selector & History */}
          <div className={`${showHistory ? 'col-span-3' : 'col-span-1'}`}>
            {/* Agent Selector */}
            <div className="bg-white border rounded-lg shadow p-4 mb-4">
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
            </div>

            {/* Toggle History */}
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="w-full mb-4 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded"
            >
              {showHistory ? '← Hide History' : 'Show History →'}
            </button>

            {/* Version History */}
            {showHistory && (
              <PromptHistory
                agentType={selectedAgent}
                onVersionSelect={loadSpecificVersion}
              />
            )}
          </div>

          {/* Main Editor Area */}
          <div className={`${showHistory ? 'col-span-9' : 'col-span-11'}`}>
            {/* Toolbar */}
            <div className="bg-white border rounded-lg shadow p-4 mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-600">
                    Current: <span className="font-mono font-semibold">v{version}</span>
                  </span>
                  <button
                    onClick={() => setPreviewMode(!previewMode)}
                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                  >
                    {previewMode ? '📝 Edit' : '👁️ Preview'}
                  </button>
                </div>

                <button
                  onClick={loadActivePrompt}
                  disabled={loading}
                  className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800"
                >
                  {loading ? 'Loading...' : '🔄 Reload Active'}
                </button>
              </div>
            </div>

            {/* AI Assistant Helper */}
            <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg shadow p-4 mb-4">
              <div className="flex items-start gap-3">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    ✨ AI Assistant (Workshopper)
                  </label>
                  <input
                    type="text"
                    value={assistRequest}
                    onChange={(e) => setAssistRequest(e.target.value)}
                    placeholder="E.g., 'Add error handling guidelines' or 'Make it more concise'"
                    className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-purple-500"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        getAiAssistance();
                      }
                    }}
                  />
                </div>
                <button
                  onClick={getAiAssistance}
                  disabled={aiAssisting || !assistRequest}
                  className="mt-6 px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                >
                  {aiAssisting ? '🤖 Thinking...' : '✨ Get Help'}
                </button>
              </div>
              <p className="text-xs text-gray-600 mt-2">
                Describe what you want to improve and the AI will suggest additions to your prompt
              </p>
            </div>

            {/* Editor / Preview */}
            <div className="bg-white border rounded-lg shadow p-6 mb-4">
              {previewMode ? (
                <div className="prose max-w-none">
                  <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-4 rounded border">
                    {promptText}
                  </pre>
                </div>
              ) : (
                <textarea
                  value={promptText}
                  onChange={(e) => setPromptText(e.target.value)}
                  className="w-full h-96 font-mono text-sm border rounded p-4 focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter prompt text..."
                />
              )}

              <div className="mt-4 text-xs text-gray-500">
                {promptText.length} characters
                {' • '}
                {promptText.split('\n').length} lines
              </div>
            </div>

            {/* Metadata Form */}
            <div className="bg-white border rounded-lg shadow p-6 mb-4">
              <h3 className="font-semibold text-gray-900 mb-4">Version Metadata</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    New Version (e.g., 1.1.0)
                  </label>
                  <input
                    type="text"
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    placeholder="1.0.0"
                    className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Created By
                  </label>
                  <input
                    type="text"
                    value={createdBy}
                    onChange={(e) => setCreatedBy(e.target.value)}
                    placeholder="user-1"
                    className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="What changed in this version?"
                  className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-blue-500"
                  rows={3}
                />
              </div>
            </div>

            {/* Actions */}
            <div className="bg-white border rounded-lg shadow p-6">
              <div className="flex items-center justify-between">
                <div className="flex gap-3">
                  <button
                    onClick={createNewVersion}
                    disabled={saving || !version || !promptText}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Create New Version'}
                  </button>

                  <button
                    onClick={createPatch}
                    disabled={saving || !promptText}
                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                  >
                    {saving ? 'Creating...' : 'Create Patch (Auto-Increment)'}
                  </button>
                </div>

                <div className="text-sm text-gray-500">
                  Changes are NOT auto-saved
                </div>
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
          </div>
        </div>
      </div>
    </div>
  );
}
