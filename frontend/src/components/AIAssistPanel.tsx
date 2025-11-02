/**
 * AI Assist Panel Component
 * 
 * Reusable AI assistant UI that can be embedded anywhere in the app.
 * Provides consistent UX for getting AI help with content.
 * 
 * Usage:
 * ```tsx
 * <AIAssistPanel
 *   placeholder="Describe what you want to improve..."
 *   context="Writing API documentation"
 *   onSuggestion={(suggestion) => {
 *     // Handle the AI suggestion
 *     setContent(prev => prev + "\n\n" + suggestion);
 *   }}
 * />
 * ```
 */
import { useState } from 'react';
import { useAiAssist } from '../hooks/useAiAssist';

interface AIAssistPanelProps {
  placeholder?: string;
  context?: string;
  onSuggestion: (suggestion: string) => void;
  onError?: (error: string) => void;
  className?: string;
  compact?: boolean;
}

export default function AIAssistPanel({
  placeholder = "Describe what you want help with...",
  context,
  onSuggestion,
  onError,
  className = "",
  compact = false
}: AIAssistPanelProps) {
  const [request, setRequest] = useState('');
  const { getSuggestion, loading, error, clearError } = useAiAssist();

  const handleSubmit = async () => {
    if (!request.trim()) return;

    const suggestion = await getSuggestion({
      prompt: request,
      context: context
    });

    if (suggestion) {
      onSuggestion(suggestion);
      setRequest('');
    } else if (error && onError) {
      onError(error);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className={`bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg shadow ${className}`}>
      <div className={compact ? "p-3" : "p-4"}>
        <div className="flex items-start gap-3">
          <div className="flex-1">
            {!compact && (
              <label className="block text-sm font-medium text-gray-700 mb-2">
                ✨ AI Assistant
              </label>
            )}
            <input
              type="text"
              value={request}
              onChange={(e) => {
                setRequest(e.target.value);
                if (error) clearError();
              }}
              placeholder={placeholder}
              className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-purple-500 text-sm"
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
          </div>
          <button
            onClick={handleSubmit}
            disabled={loading || !request.trim()}
            className={`${compact ? 'mt-0' : 'mt-6'} px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap text-sm`}
          >
            {loading ? '🤖 ...' : '✨ Help'}
          </button>
        </div>
        
        {!compact && (
          <p className="text-xs text-gray-600 mt-2">
            Press Enter or click Help to get AI suggestions
          </p>
        )}
        
        {error && (
          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-xs">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
