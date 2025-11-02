/**
 * Prompt Comparison Component
 * 
 * Side-by-side comparison of two prompt versions with:
 * - Two-column layout
 * - Character/line count comparison
 * - Basic diff highlighting
 * - Metadata display
 */
import { useState, useEffect } from 'react';

interface PromptData {
  agent_type: string;
  version: string;
  prompt_text: string;
  is_active: boolean;
}

interface PromptComparisonProps {
  agentType: string;
  versionA: string;
  versionB: string;
  onPromote?: (version: string) => void;
}

export default function PromptComparison({
  agentType,
  versionA,
  versionB,
  onPromote
}: PromptComparisonProps) {
  const [promptA, setPromptA] = useState<PromptData | null>(null);
  const [promptB, setPromptB] = useState<PromptData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPrompts();
  }, [agentType, versionA, versionB]);

  const loadPrompts = async () => {
    try {
      setLoading(true);
      setError(null);

      const [resA, resB] = await Promise.all([
        fetch(`/api/v1/prompts/${agentType}/${versionA}`),
        fetch(`/api/v1/prompts/${agentType}/${versionB}`)
      ]);

      if (!resA.ok || !resB.ok) {
        throw new Error('Failed to load one or both versions');
      }

      const [dataA, dataB] = await Promise.all([resA.json(), resB.json()]);
      setPromptA(dataA);
      setPromptB(dataB);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompts');
    } finally {
      setLoading(false);
    }
  };

  // Simple diff: find lines that are different
  const getDiff = () => {
    if (!promptA || !promptB) return { linesA: [], linesB: [], different: [] };

    const linesA = promptA.prompt_text.split('\n');
    const linesB = promptB.prompt_text.split('\n');
    const different: number[] = [];

    const maxLength = Math.max(linesA.length, linesB.length);
    for (let i = 0; i < maxLength; i++) {
      if (linesA[i] !== linesB[i]) {
        different.push(i);
      }
    }

    return { linesA, linesB, different };
  };

  if (loading) {
    return (
      <div className="bg-white border rounded-lg shadow p-8 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading comparison...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        Error: {error}
      </div>
    );
  }

  if (!promptA || !promptB) {
    return null;
  }

  const { linesA, linesB, different } = getDiff();
  const diffCount = different.length;
  const diffPercentage = Math.round((diffCount / Math.max(linesA.length, linesB.length)) * 100);

  return (
    <div className="bg-white border rounded-lg shadow">
      {/* Header */}
      <div className="px-6 py-4 border-b bg-gray-50">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Comparison: {agentType}
          </h3>
          <div className="text-sm text-gray-600">
            {diffCount} line{diffCount !== 1 ? 's' : ''} different ({diffPercentage}%)
          </div>
        </div>
      </div>

      {/* Metadata Comparison */}
      <div className="px-6 py-4 border-b bg-gray-50 grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="font-semibold mb-2">Version A</div>
          <div className="space-y-1">
            <div>
              <span className="font-mono">v{promptA.version}</span>
              {promptA.is_active && (
                <span className="ml-2 px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded">
                  Active
                </span>
              )}
            </div>
            <div className="text-gray-600">
              {promptA.prompt_text.length} chars, {linesA.length} lines
            </div>
          </div>
        </div>

        <div>
          <div className="font-semibold mb-2">Version B</div>
          <div className="space-y-1">
            <div>
              <span className="font-mono">v{promptB.version}</span>
              {promptB.is_active && (
                <span className="ml-2 px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded">
                  Active
                </span>
              )}
            </div>
            <div className="text-gray-600">
              {promptB.prompt_text.length} chars, {linesB.length} lines
            </div>
          </div>
        </div>
      </div>

      {/* Side-by-Side Comparison */}
      <div className="grid grid-cols-2 divide-x">
        {/* Version A */}
        <div className="p-4 overflow-auto max-h-96">
          <div className="text-xs font-semibold text-gray-600 mb-2 sticky top-0 bg-white">
            Version {promptA.version}
          </div>
          <pre className="text-xs font-mono whitespace-pre-wrap">
            {linesA.map((line, idx) => (
              <div
                key={idx}
                className={`${
                  different.includes(idx)
                    ? 'bg-red-50 border-l-2 border-red-400 pl-2'
                    : ''
                }`}
              >
                <span className="text-gray-400 select-none mr-2">{idx + 1}</span>
                {line}
              </div>
            ))}
          </pre>
        </div>

        {/* Version B */}
        <div className="p-4 overflow-auto max-h-96">
          <div className="text-xs font-semibold text-gray-600 mb-2 sticky top-0 bg-white">
            Version {promptB.version}
          </div>
          <pre className="text-xs font-mono whitespace-pre-wrap">
            {linesB.map((line, idx) => (
              <div
                key={idx}
                className={`${
                  different.includes(idx)
                    ? 'bg-green-50 border-l-2 border-green-400 pl-2'
                    : ''
                }`}
              >
                <span className="text-gray-400 select-none mr-2">{idx + 1}</span>
                {line}
              </div>
            ))}
          </pre>
        </div>
      </div>

      {/* Actions */}
      {onPromote && (
        <div className="px-6 py-4 border-t bg-gray-50">
          <div className="flex gap-3">
            <button
              onClick={() => onPromote(promptA.version)}
              disabled={promptA.is_active}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Promote v{promptA.version} to Active
            </button>
            <button
              onClick={() => onPromote(promptB.version)}
              disabled={promptB.is_active}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Promote v{promptB.version} to Active
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
