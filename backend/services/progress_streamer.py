"""
Progress Streamer Service

WebSocket/SSE streaming for real-time build progress updates.
Subscribes to EventBus and streams events to frontend.

Reference: Phase 3.5 - Backend Integration
"""
import logging
import asyncio
from typing import Dict, Set, Any
from fastapi import WebSocket, WebSocketDisconnect

from backend.services.event_bus import EventBus, Event, get_event_bus

logger = logging.getLogger(__name__)


class ProgressStreamer:
    """
    Service for streaming build progress via WebSocket.
    
    Features:
    - WebSocket connection management
    - Subscribe to EventBus per project
    - Stream events to connected clients
    - Handle disconnections gracefully
    
    Example:
        streamer = ProgressStreamer()
        
        # In WebSocket endpoint:
        await streamer.connect(websocket, project_id)
        await streamer.stream(project_id)
    """
    
    def __init__(self, event_bus: EventBus = None):
        """Initialize progress streamer."""
        self.event_bus = event_bus or get_event_bus()
        
        # Active connections: {project_id: {websocket, websocket, ...}}
        self.connections: Dict[str, Set[WebSocket]] = {}
        
        logger.info("ProgressStreamer initialized")
    
    async def connect(self, websocket: WebSocket, project_id: str) -> None:
        """
        Accept WebSocket connection and subscribe to project events.
        
        Args:
            websocket: WebSocket connection
            project_id: Project to stream
        """
        await websocket.accept()
        
        if project_id not in self.connections:
            self.connections[project_id] = set()
            
            # Subscribe to project events
            async def on_event(event: Event):
                await self._broadcast_event(project_id, event)
            
            self.event_bus.subscribe_project(project_id, on_event)
        
        self.connections[project_id].add(websocket)
        logger.info(f"WebSocket connected: project={project_id}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "project_id": project_id,
            "message": "Connected to build stream"
        })
    
    async def disconnect(self, websocket: WebSocket, project_id: str) -> None:
        """
        Handle WebSocket disconnection.
        
        Args:
            websocket: WebSocket connection
            project_id: Project identifier
        """
        if project_id in self.connections:
            self.connections[project_id].discard(websocket)
            
            if not self.connections[project_id]:
                del self.connections[project_id]
        
        logger.info(f"WebSocket disconnected: project={project_id}")
    
    async def stream(self, websocket: WebSocket, project_id: str) -> None:
        """
        Main streaming loop - keeps connection alive until client disconnects.
        
        Args:
            websocket: WebSocket connection
            project_id: Project identifier
        """
        try:
            # Keep connection alive
            while True:
                # Receive messages from client (ping/pong)
                message = await websocket.receive_text()
                
                if message == "ping":
                    await websocket.send_json({"type": "pong"})
        
        except WebSocketDisconnect:
            await self.disconnect(websocket, project_id)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await self.disconnect(websocket, project_id)
    
    async def _broadcast_event(self, project_id: str, event: Event) -> None:
        """
        Broadcast event to all connected clients for project.
        
        Args:
            project_id: Project identifier
            event: Event to broadcast
        """
        if project_id not in self.connections:
            return
        
        # Convert event to JSON-serializable dict
        event_data = {
            "type": "event",
            "event_type": event.event_type,
            "project_id": event.project_id,
            "timestamp": event.timestamp,
            "data": event.data,
            "agent_id": event.agent_id,
            "task_id": event.task_id
        }
        
        # Send to all connected clients
        disconnected = []
        for websocket in self.connections[project_id]:
            try:
                await websocket.send_json(event_data)
            except Exception as e:
                logger.error(f"Failed to send event: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            self.connections[project_id].discard(websocket)


# Global instance
_progress_streamer: ProgressStreamer = None


def get_progress_streamer() -> ProgressStreamer:
    """Get global progress streamer instance."""
    global _progress_streamer
    if _progress_streamer is None:
        _progress_streamer = ProgressStreamer()
    return _progress_streamer
