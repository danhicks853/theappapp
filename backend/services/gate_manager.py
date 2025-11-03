"""
Gate Manager Service

Manages human approval gates for agent escalations.
Handles gate creation, approval, denial, and lifecycle management.

Reference: Section 1.3 - Decision-Making & Escalation System
"""
import logging
from typing import List, Optional, Dict, Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class GateManager:
    """
    Service for managing human approval gates.
    
    Features:
    - Create gates for agent escalations
    - Approve or deny gates with feedback
    - Query pending gates
    - Resolve gates and resume agents
    
    Gate Types:
    - loop_detected: Agent hit 3 identical failures
    - high_risk: Operation requires human review
    - collaboration_deadlock: Agents in collaboration loop
    - manual: User manually paused agent
    
    Example:
        gate_mgr = GateManager(engine)
        gate_id = await gate_mgr.create_gate(
            project_id="proj-123",
            agent_id="backend-dev-1",
            gate_type="loop_detected",
            reason="3 identical test failures",
            context={"error": "...", "attempts": 3}
        )
        await gate_mgr.approve_gate(gate_id, resolved_by="user-1", feedback="Try different approach")
    """
    
    def __init__(self, engine: Engine):
        """Initialize gate manager with database engine."""
        self.engine = engine
        logger.info("GateManager initialized")
    
    async def create_gate(
        self,
        project_id: str,
        agent_id: str,
        gate_type: str,
        reason: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Create a new human approval gate.
        
        Args:
            project_id: Project identifier
            agent_id: Agent identifier that triggered the gate
            gate_type: Type of gate ('loop_detected', 'high_risk', 'collaboration_deadlock', 'manual')
            reason: Human-readable reason for the gate
            context: Additional context as JSON (error details, state, etc.)
        
        Returns:
            Gate ID (UUID as string)
        """
        logger.info(f"Creating gate: type={gate_type}, agent={agent_id}, project={project_id}")
        import json
        
        query = text("""
            INSERT INTO gates (project_id, agent_id, gate_type, reason, context, status, created_at)
            VALUES (:project_id, :agent_id, :gate_type, :reason, :context, 'pending', NOW())
            RETURNING id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "project_id": project_id,
                "agent_id": agent_id,
                "gate_type": gate_type,
                "reason": reason,
                "context": json.dumps(context) if context else None
            })
            conn.commit()
            
            gate_id = result.scalar()
            logger.info(f"Gate created: id={gate_id}")
            return str(gate_id)
    
    async def approve_gate(
        self,
        gate_id: str,
        resolved_by: str,
        feedback: Optional[str] = None
    ) -> bool:
        """
        Approve a gate and allow agent to continue.
        
        Args:
            gate_id: Gate identifier
            resolved_by: User who approved the gate
            feedback: Optional feedback/instructions for the agent
        
        Returns:
            True if approved successfully, False if gate not found or already resolved
        """
        logger.info(f"Approving gate: id={gate_id}, by={resolved_by}")
        
        query = text("""
            UPDATE gates
            SET status = 'approved',
                resolved_at = NOW(),
                resolved_by = :resolved_by,
                feedback = :feedback
            WHERE id = :gate_id AND status = 'pending'
            RETURNING id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "gate_id": gate_id,
                "resolved_by": resolved_by,
                "feedback": feedback
            })
            conn.commit()
            
            if result.rowcount > 0:
                logger.info(f"Gate approved: id={gate_id}")
                return True
            else:
                logger.warning(f"Gate not found or already resolved: id={gate_id}")
                return False
    
    async def deny_gate(
        self,
        gate_id: str,
        resolved_by: str,
        feedback: str
    ) -> bool:
        """
        Deny a gate and stop the agent.
        
        Args:
            gate_id: Gate identifier
            resolved_by: User who denied the gate
            feedback: Required feedback explaining why denied
        
        Returns:
            True if denied successfully, False if gate not found or already resolved
        """
        logger.info(f"Denying gate: id={gate_id}, by={resolved_by}")
        
        if not feedback:
            logger.error("Feedback is required when denying a gate")
            raise ValueError("Feedback is required when denying a gate")
        
        query = text("""
            UPDATE gates
            SET status = 'denied',
                resolved_at = NOW(),
                resolved_by = :resolved_by,
                feedback = :feedback
            WHERE id = :gate_id AND status = 'pending'
            RETURNING id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {
                "gate_id": gate_id,
                "resolved_by": resolved_by,
                "feedback": feedback
            })
            conn.commit()
            
            if result.rowcount > 0:
                logger.info(f"Gate denied: id={gate_id}")
                return True
            else:
                logger.warning(f"Gate not found or already resolved: id={gate_id}")
                return False
    
    async def get_pending_gates(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all pending gates, optionally filtered by project.
        
        Args:
            project_id: Optional project ID to filter by
        
        Returns:
            List of gate dictionaries with all fields
        """
        if project_id:
            logger.debug(f"Fetching pending gates for project: {project_id}")
            query = text("""
                SELECT id, project_id, agent_id, gate_type, reason, context, 
                       status, created_at, resolved_at, resolved_by, feedback
                FROM gates
                WHERE project_id = :project_id AND status = 'pending'
                ORDER BY created_at DESC
            """)
            params = {"project_id": project_id}
        else:
            logger.debug("Fetching all pending gates")
            query = text("""
                SELECT id, project_id, agent_id, gate_type, reason, context,
                       status, created_at, resolved_at, resolved_by, feedback
                FROM gates
                WHERE status = 'pending'
                ORDER BY created_at DESC
            """)
            params = {}
        
        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            
            gates = [
                {
                    "id": str(row[0]),
                    "project_id": str(row[1]),
                    "agent_id": row[2],
                    "gate_type": row[3],
                    "reason": row[4],
                    "context": row[5],
                    "status": row[6],
                    "created_at": row[7].isoformat() if row[7] else None,
                    "resolved_at": row[8].isoformat() if row[8] else None,
                    "resolved_by": row[9],
                    "feedback": row[10]
                }
                for row in rows
            ]
            
            logger.info(f"Found {len(gates)} pending gates")
            return gates
    
    async def get_gate(self, gate_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific gate by ID.
        
        Args:
            gate_id: Gate identifier
        
        Returns:
            Gate dictionary or None if not found
        """
        logger.debug(f"Fetching gate: id={gate_id}")
        
        query = text("""
            SELECT id, project_id, agent_id, gate_type, reason, context,
                   status, created_at, resolved_at, resolved_by, feedback
            FROM gates
            WHERE id = :gate_id
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"gate_id": gate_id})
            row = result.fetchone()
            
            if row:
                return {
                    "id": str(row[0]),
                    "project_id": str(row[1]),
                    "agent_id": row[2],
                    "gate_type": row[3],
                    "reason": row[4],
                    "context": row[5],
                    "status": row[6],
                    "created_at": row[7].isoformat() if row[7] else None,
                    "resolved_at": row[8].isoformat() if row[8] else None,
                    "resolved_by": row[9],
                    "feedback": row[10]
                }
            else:
                logger.warning(f"Gate not found: id={gate_id}")
                return None
    
    async def handle_rejection(
        self,
        gate_id: str,
        resolved_by: str,
        feedback: str,
        revision_count: int = 0
    ) -> Dict[str, Any]:
        """
        Handle gate rejection with resolution cycle.
        
        Flow:
        1. User denies gate with feedback
        2. Agent receives feedback
        3. Agent revises approach (up to 3 attempts)
        4. Agent resubmits for approval
        5. After 3 rejections, escalate to human for manual intervention
        
        Args:
            gate_id: Gate identifier
            resolved_by: User who rejected the gate
            feedback: Required feedback explaining rejection and suggested approach
            revision_count: Current revision attempt count
        
        Returns:
            Dict with status, next_action, and escalation info
        """
        logger.info(f"Handling rejection for gate: id={gate_id}, revision={revision_count}")
        
        MAX_REVISIONS = 3
        
        # Deny the gate with feedback
        denied = await self.deny_gate(gate_id, resolved_by, feedback)
        
        if not denied:
            logger.error(f"Failed to deny gate: {gate_id}")
            return {
                "success": False,
                "error": "Failed to deny gate"
            }
        
        # Check revision count
        if revision_count >= MAX_REVISIONS:
            logger.warning(f"Max revisions reached for gate: {gate_id}, escalating")
            
            # Create escalation gate
            gate = await self.get_gate(gate_id)
            if gate:
                escalation_gate_id = await self.create_gate(
                    project_id=gate["project_id"],
                    agent_id=gate["agent_id"],
                    gate_type="manual",
                    reason=f"Agent failed after {MAX_REVISIONS} revision attempts. Manual intervention required.",
                    context={
                        "original_gate_id": gate_id,
                        "revision_attempts": revision_count,
                        "last_feedback": feedback,
                        "escalation": True
                    }
                )
                
                return {
                    "success": True,
                    "status": "escalated",
                    "next_action": "manual_intervention",
                    "escalation_gate_id": escalation_gate_id,
                    "message": f"Max revisions ({MAX_REVISIONS}) reached. Created escalation gate for manual review."
                }
        
        # Return feedback to agent for revision
        return {
            "success": True,
            "status": "rejected",
            "next_action": "revise_and_resubmit",
            "feedback": feedback,
            "revision_count": revision_count + 1,
            "remaining_attempts": MAX_REVISIONS - revision_count - 1,
            "message": f"Gate rejected. Agent should revise approach based on feedback. {MAX_REVISIONS - revision_count - 1} attempts remaining."
        }
    
    async def get_rejection_history(self, gate_id: str) -> List[Dict[str, Any]]:
        """
        Get rejection history for a gate to track revision cycles.
        
        Args:
            gate_id: Gate identifier
        
        Returns:
            List of rejection events with feedback
        """
        # Note: This would require a separate gate_history table to track all rejections
        # For now, we just return the current gate's feedback if denied
        gate = await self.get_gate(gate_id)
        
        if not gate:
            return []
        
        if gate["status"] == "denied" and gate["feedback"]:
            return [
                {
                    "gate_id": gate["id"],
                    "resolved_at": gate["resolved_at"],
                    "resolved_by": gate["resolved_by"],
                    "feedback": gate["feedback"],
                    "status": gate["status"]
                }
            ]
        
        return []
