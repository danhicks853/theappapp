/**
 * useAiAssist Hook
 * 
 * Reusable hook for AI assistance throughout the UI.
 * Can be used anywhere users need help with content generation or improvement.
 * 
 * Usage:
 * ```tsx
 * const { getSuggestion, loading, error } = useAiAssist();
 * 
 * const handleHelp = async () => {
 *   const suggestion = await getSuggestion({
 *     prompt: "Add error handling guidelines",
 *     context: "Backend development prompt"
 *   });
 *   if (suggestion) {
 *     // Use the suggestion
 *   }
 * };
 * ```
 */
import { useState } from 'react';

interface AIAssistRequest {
  prompt: string;
  context?: string;
}

interface AIAssistResponse {
  suggestion: string;
}

interface UseAiAssistReturn {
  getSuggestion: (request: AIAssistRequest) => Promise<string | null>;
  loading: boolean;
  error: string | null;
  clearError: () => void;
}

export function useAiAssist(): UseAiAssistReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getSuggestion = async (request: AIAssistRequest): Promise<string | null> => {
    if (!request.prompt) {
      setError('Please provide a prompt');
      return null;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/v1/specialists/ai-assist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ 
          detail: `Failed: ${response.statusText}` 
        }));
        throw new Error(errorData.detail || 'Failed to get AI assistance');
      }

      const data: AIAssistResponse = await response.json();
      return data.suggestion;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get AI assistance';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const clearError = () => setError(null);

  return { getSuggestion, loading, error, clearError };
}
