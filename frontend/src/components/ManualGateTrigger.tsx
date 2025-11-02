/**
 * Manual Gate Trigger Component
 * 
 * Allows users to manually pause an agent for review.
 * Creates a "manual" gate and pauses the agent until approved/denied.
 * 
 * Usage:
 * ```tsx
 * <ManualGateTrigger
 *   projectId="proj-123"
 *   agentId="backend-1"
 *   agentName="Backend Developer"
 *   onGateCreated={(gateId) => console.log('Gate created:', gateId)}
 * />
 * ```
 */
import { useState } from 'react';

interface ManualGateTriggerProps {
  projectId: string;
  agentId: string;
  agentName: string;
  onGateCreated?: (gateId: string) => void;
  onError?: (error: string) => void;
  compact?: boolean;
}

export default function ManualGateTrigger({
  projectId,
  agentId,
  agentName,
  onGateCreated,
  onError,
  compact = false
}: ManualGateTriggerProps) {
  const [showDialog, setShowDialog] = useState(false);
  const [reason, setReason] = useState('');
  const [creating, setCreating] = useState(false);

  const handleTrigger = async () => {
    if (!reason.trim()) {
      onError?.('Please provide a reason for pausing');
      return;
    }

    try {
      setCreating(true);

      const response = await fetch('/api/v1/gates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          agent_id: agentId,
          gate_type: 'manual',
          reason: reason.trim(),
          context: {
            agent_name: agentName,
            manual_trigger: true,
            timestamp: new Date().toISOString()
          }
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to create gate');
      }

      const data = await response.json();
      const gateId = data.gate_id || data.id;

      onGateCreated?.(gateId);
      setShowDialog(false);
      setReason('');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to pause agent';
      onError?.(errorMsg);
    } finally {
      setCreating(false);
    }
  };

  if (compact) {
    return (
      <>
        <button
          onClick={() => setShowDialog(true)}
          className="px-3 py-1 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700 flex items-center gap-1"
          title="Pause agent for review"
        >
          ⏸️ Pause
        </button>

        {showDialog && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full">
              <h3 className="text-lg font-semibold mb-4">Pause Agent for Review</h3>
              
              <p className="text-sm text-gray-600 mb-4">
                Agent <strong>{agentName}</strong> will be paused until you approve or deny this gate.
              </p>

              <label className="block text-sm font-medium text-gray-700 mb-2">
                Reason for pausing:
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="E.g., Need to review approach before continuing..."
                className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-yellow-500 mb-4"
                rows={3}
                disabled={creating}
              />

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowDialog(false);
                    setReason('');
                  }}
                  disabled={creating}
                  className="px-4 py-2 text-gray-700 border rounded hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleTrigger}
                  disabled={creating || !reason.trim()}
                  className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50"
                >
                  {creating ? 'Pausing...' : '⏸️ Pause Agent'}
                </button>
              </div>
            </div>
          </div>
        )}
      </>
    );
  }

  // Full mode
  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <div className="text-2xl">⏸️</div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-1">Manual Review Gate</h3>
          <p className="text-sm text-gray-600 mb-3">
            Pause <strong>{agentName}</strong> to review its work before continuing.
          </p>

          {!showDialog ? (
            <button
              onClick={() => setShowDialog(true)}
              className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
            >
              Pause for Review
            </button>
          ) : (
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">
                Reason for pausing:
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="E.g., Need to review approach before continuing..."
                className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-yellow-500"
                rows={3}
                disabled={creating}
              />

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowDialog(false);
                    setReason('');
                  }}
                  disabled={creating}
                  className="px-4 py-2 text-gray-700 border rounded hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleTrigger}
                  disabled={creating || !reason.trim()}
                  className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50"
                >
                  {creating ? 'Creating Gate...' : '⏸️ Create Gate'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
