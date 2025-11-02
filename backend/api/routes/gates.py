"""API endpoints for human approval gates."""

from __future__ import annotations

from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.dependencies import get_gate_manager
from backend.services.gate_manager import GateManager


router = APIRouter(prefix="/api/v1/gates", tags=["gates"])


class CreateGateRequest(BaseModel):
    project_id: str = Field(..., description="Project identifier")
    agent_id: str = Field(..., description="Agent identifier")
    gate_type: str = Field(..., description="Gate type: loop_detected, high_risk, collaboration_deadlock, manual")
    reason: str = Field(..., description="Human-readable reason for the gate")
    context: Dict[str, Any] = Field(..., description="Additional context as JSON")


class ResolveGateRequest(BaseModel):
    resolved_by: str = Field(..., description="User who resolved the gate")
    feedback: Optional[str] = Field(None, description="Optional feedback for approval, required for denial")


class GateResponse(BaseModel):
    id: str
    project_id: str
    agent_id: str
    gate_type: str
    reason: str
    context: Dict[str, Any]
    status: str
    created_at: Optional[str]
    resolved_at: Optional[str]
    resolved_by: Optional[str]
    feedback: Optional[str]


@router.post("", response_model=Dict[str, str])
async def create_gate(
    payload: CreateGateRequest,
    gate_mgr: GateManager = Depends(get_gate_manager),
) -> Dict[str, str]:
    """Create a new human approval gate.
    
    Args:
        payload: Gate creation parameters
        gate_mgr: GateManager instance (injected)
    
    Returns:
        Dictionary with gate_id
    """
    gate_id = await gate_mgr.create_gate(
        project_id=payload.project_id,
        agent_id=payload.agent_id,
        gate_type=payload.gate_type,
        reason=payload.reason,
        context=payload.context
    )
    
    return {"gate_id": gate_id}


@router.get("", response_model=List[GateResponse])
async def get_pending_gates(
    project_id: Optional[str] = None,
    gate_mgr: GateManager = Depends(get_gate_manager),
) -> List[GateResponse]:
    """Get all pending gates, optionally filtered by project.
    
    Args:
        project_id: Optional project ID filter
        gate_mgr: GateManager instance (injected)
    
    Returns:
        List of pending gates
    """
    gates = await gate_mgr.get_pending_gates(project_id=project_id)
    return [GateResponse(**gate) for gate in gates]


@router.get("/{gate_id}", response_model=GateResponse)
async def get_gate(
    gate_id: str,
    gate_mgr: GateManager = Depends(get_gate_manager),
) -> GateResponse:
    """Get a specific gate by ID.
    
    Args:
        gate_id: Gate identifier
        gate_mgr: GateManager instance (injected)
    
    Returns:
        Gate details
    
    Raises:
        HTTPException: 404 if gate not found
    """
    gate = await gate_mgr.get_gate(gate_id)
    
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    
    return GateResponse(**gate)


@router.post("/{gate_id}/approve", response_model=Dict[str, str])
async def approve_gate(
    gate_id: str,
    payload: ResolveGateRequest,
    gate_mgr: GateManager = Depends(get_gate_manager),
) -> Dict[str, str]:
    """Approve a gate and allow agent to continue.
    
    Args:
        gate_id: Gate identifier
        payload: Resolution details
        gate_mgr: GateManager instance (injected)
    
    Returns:
        Success status
    
    Raises:
        HTTPException: 404 if gate not found or already resolved
    """
    success = await gate_mgr.approve_gate(
        gate_id=gate_id,
        resolved_by=payload.resolved_by,
        feedback=payload.feedback
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Gate not found or already resolved")
    
    return {"status": "approved", "gate_id": gate_id}


@router.post("/{gate_id}/deny", response_model=Dict[str, str])
async def deny_gate(
    gate_id: str,
    payload: ResolveGateRequest,
    gate_mgr: GateManager = Depends(get_gate_manager),
) -> Dict[str, str]:
    """Deny a gate and stop the agent.
    
    Args:
        gate_id: Gate identifier
        payload: Resolution details (feedback required)
        gate_mgr: GateManager instance (injected)
    
    Returns:
        Success status
    
    Raises:
        HTTPException: 400 if feedback missing, 404 if gate not found
    """
    if not payload.feedback:
        raise HTTPException(status_code=400, detail="Feedback is required when denying a gate")
    
    success = await gate_mgr.deny_gate(
        gate_id=gate_id,
        resolved_by=payload.resolved_by,
        feedback=payload.feedback
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Gate not found or already resolved")
    
    return {"status": "denied", "gate_id": gate_id}
