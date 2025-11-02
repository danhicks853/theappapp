/**
 * Gate Approval Modal
 * 
 * Modal for reviewing and resolving gates (approve or deny).
 * Shows gate details, agent context, and collects feedback.
 * 
 * Usage:
 * ```tsx
 * <GateApprovalModal
 *   gate={gateData}
 *   onClose={() => setShowModal(false)}
 *   onResolved={() => {
 *     loadGates();
 *     setShowModal(false);
 *   }}
 * />
 * ```
 */
import { useState } from 'react';

interface Gate {
  id: string;
  project_id: string;
  agent_id: string;
  gate_type: string;
  reason: string;
  context: any;
  status: string;
  created_at: string;
}

interface GateApprovalModalProps {
  gate: Gate;
  onClose: () => void;
  onResolved?: (gateId: string, approved: boolean) => void;
  onError?: (error: string) => void;
}

export default function GateApprovalModal({
  gate,
  onClose,
  onResolved,
  onError
}: GateApprovalModalProps) {
  const [feedback, setFeedback] = useState('');
  const [resolving, setResolving] = useState(false);
  const [action, setAction] = useState<'approve' | 'deny' | null>(null);

  const handleResolve = async (approved: boolean) => {
    if (!approved && !feedback.trim()) {
      onError?.('Feedback is required when denying a gate');
      return;
    }

    setAction(approved ? 'approve' : 'deny');
    setResolving(true);

    try {
      const endpoint = approved 
        ? `/api/v1/gates/${gate.id}/approve`
        : `/api/v1/gates/${gate.id}/deny`;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resolved_by: 'user', // TODO: Get from auth context
          feedback: feedback.trim() || (approved ? 'Approved' : undefined)
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Failed to ${approved ? 'approve' : 'deny'} gate`);
      }

      onResolved?.(gate.id, approved);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to resolve gate';
      onError?.(errorMsg);
      setAction(null);
      setResolving(false);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  const getGateTypeDisplay = (type: string) => {
    const types: Record<string, { label: string; icon: string; color: string }> = {
      manual: { label: 'Manual Review', icon: '⏸️', color: 'yellow' },
      loop_detected: { label: 'Loop Detected', icon: '🔁', color: 'red' },
      high_risk: { label: 'High Risk', icon: '⚠️', color: 'orange' },
      collaboration_deadlock: { label: 'Collaboration Deadlock', icon: '🔒', color: 'red' }
    };
    return types[type] || { label: type, icon: '🚧', color: 'gray' };
  };

  const gateType = getGateTypeDisplay(gate.gate_type);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className={`px-6 py-4 border-b bg-${gateType.color}-50 border-${gateType.color}-200`}>
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-2xl">{gateType.icon}</span>
                <h2 className="text-xl font-bold text-gray-900">{gateType.label}</h2>
              </div>
              <p className="text-sm text-gray-600 mt-1">
                Created {formatDate(gate.created_at)}
              </p>
            </div>
            <button
              onClick={onClose}
              disabled={resolving}
              className="text-gray-400 hover:text-gray-600 text-2xl disabled:opacity-50"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-4">
          {/* Agent Info */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Agent</label>
            <div className="px-3 py-2 bg-gray-50 rounded border">
              <span className="font-mono text-sm">{gate.agent_id}</span>
            </div>
          </div>

          {/* Reason */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Reason</label>
            <div className="px-3 py-2 bg-gray-50 rounded border">
              <p className="text-sm">{gate.reason}</p>
            </div>
          </div>

          {/* Context */}
          {gate.context && Object.keys(gate.context).length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Context</label>
              <div className="px-3 py-2 bg-gray-50 rounded border max-h-48 overflow-y-auto">
                <pre className="text-xs font-mono whitespace-pre-wrap">
                  {JSON.stringify(gate.context, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Feedback */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Feedback {action === 'deny' && <span className="text-red-600">*</span>}
            </label>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder={
                action === 'deny' 
                  ? "Required: Explain why this is denied and what should be done differently..."
                  : "Optional: Add notes about your decision..."
              }
              className={`w-full px-3 py-2 border rounded focus:ring-2 ${
                action === 'deny' && !feedback.trim()
                  ? 'border-red-300 focus:ring-red-500'
                  : 'focus:ring-blue-500'
              }`}
              rows={4}
              disabled={resolving}
            />
            <p className="text-xs text-gray-500 mt-1">
              {action === 'deny' 
                ? 'Required for denial. This helps the agent understand what went wrong.'
                : 'Optional but helpful for future reference.'}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="px-6 py-4 border-t bg-gray-50 flex gap-3 justify-end">
          <button
            onClick={onClose}
            disabled={resolving}
            className="px-4 py-2 text-gray-700 border rounded hover:bg-gray-100 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={() => handleResolve(false)}
            disabled={resolving}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {resolving && action === 'deny' ? 'Denying...' : '❌ Deny'}
          </button>
          <button
            onClick={() => handleResolve(true)}
            disabled={resolving}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {resolving && action === 'approve' ? 'Approving...' : '✅ Approve & Resume'}
          </button>
        </div>

        {/* Helper text */}
        <div className="px-6 py-3 bg-blue-50 border-t border-blue-200">
          <p className="text-xs text-blue-800">
            💡 <strong>Approve</strong> will resume the agent immediately.
            <strong> Deny</strong> will stop the agent and provide your feedback for correction.
          </p>
        </div>
      </div>
    </div>
  );
}
