"""
Event Bus Service

Central pub/sub system for broadcasting build events in real-time.
Enables progress monitoring and inter-service communication.

Reference: Phase 3.5 - Backend Integration
"""
import logging
import asyncio
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events in the system."""
    # Project events
    PROJECT_CREATED = "project_created"
    PROJECT_STARTED = "project_started"
    PROJECT_PAUSED = "project_paused"
    PROJECT_RESUMED = "project_resumed"
    PROJECT_COMPLETED = "project_completed"
    PROJECT_FAILED = "project_failed"
    
    # Agent events
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    
    # Code events
    CODE_GENERATED = "code_generated"
    FILE_CREATED = "file_created"
    FILE_UPDATED = "file_updated"
    FILE_DELETED = "file_deleted"
    
    # Testing events
    TEST_GENERATED = "test_generated"
    TEST_PASSED = "test_passed"
    TEST_FAILED = "test_failed"
    TEST_SUITE_COMPLETED = "test_suite_completed"
    
    # Gate events
    GATE_TRIGGERED = "gate_triggered"
    GATE_APPROVED = "gate_approved"
    GATE_REJECTED = "gate_rejected"
    
    # Phase events
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    DELIVERABLE_COMPLETED = "deliverable_completed"
    
    # Error events
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"
    
    # System events
    SYSTEM_CHECK = "system_check"


@dataclass
class Event:
    """Event data structure."""
    event_type: EventType
    project_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any] = field(default_factory=dict)
    agent_id: Optional[str] = None
    task_id: Optional[str] = None


class EventBus:
    """
    Central event bus for pub/sub messaging.
    
    Features:
    - Subscribe to specific event types
    - Subscribe to all events for a project
    - Publish events to subscribers
    - Async event delivery
    - Event history (limited buffer)
    
    Example:
        bus = EventBus()
        
        # Subscribe to code generation events
        async def on_code_generated(event: Event):
            print(f"Code generated: {event.data['file_path']}")
        
        bus.subscribe(EventType.CODE_GENERATED, on_code_generated)
        
        # Publish event
        await bus.publish(Event(
            event_type=EventType.CODE_GENERATED,
            project_id="proj-123",
            data={"file_path": "backend/services/user.py", "lines": 150}
        ))
    """
    
    def __init__(self, history_size: int = 1000):
        """
        Initialize event bus.
        
        Args:
            history_size: Max events to keep in history per project
        """
        # Event type subscribers: {event_type: [callbacks]}
        self._type_subscribers: Dict[EventType, List[Callable]] = {}
        
        # Project subscribers: {project_id: [callbacks]}
        self._project_subscribers: Dict[str, List[Callable]] = {}
        
        # Global subscribers (receive all events)
        self._global_subscribers: List[Callable] = []
        
        # Event history: {project_id: [events]}
        self._history: Dict[str, List[Event]] = {}
        self._history_size = history_size
        
        logger.info("EventBus initialized")
    
    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], Any]
    ) -> None:
        """
        Subscribe to specific event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Async callback function(event) -> None
        """
        if event_type not in self._type_subscribers:
            self._type_subscribers[event_type] = []
        
        self._type_subscribers[event_type].append(callback)
        logger.info(f"Subscribed to {event_type}")
    
    def subscribe_project(
        self,
        project_id: str,
        callback: Callable[[Event], Any]
    ) -> None:
        """
        Subscribe to all events for a specific project.
        
        Args:
            project_id: Project identifier
            callback: Async callback function(event) -> None
        """
        if project_id not in self._project_subscribers:
            self._project_subscribers[project_id] = []
        
        self._project_subscribers[project_id].append(callback)
        logger.info(f"Subscribed to project: {project_id}")
    
    def subscribe_global(
        self,
        callback: Callable[[Event], Any]
    ) -> None:
        """
        Subscribe to all events across all projects.
        
        Args:
            callback: Async callback function(event) -> None
        """
        self._global_subscribers.append(callback)
        logger.info("Added global subscriber")
    
    def unsubscribe(
        self,
        event_type: Optional[EventType] = None,
        project_id: Optional[str] = None,
        callback: Optional[Callable] = None
    ) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            event_type: Event type to unsubscribe from
            project_id: Project to unsubscribe from
            callback: Specific callback to remove
        
        Returns:
            True if unsubscribed successfully
        """
        if event_type and callback:
            if event_type in self._type_subscribers:
                try:
                    self._type_subscribers[event_type].remove(callback)
                    return True
                except ValueError:
                    pass
        
        if project_id and callback:
            if project_id in self._project_subscribers:
                try:
                    self._project_subscribers[project_id].remove(callback)
                    return True
                except ValueError:
                    pass
        
        return False
    
    async def publish(self, event: Event) -> None:
        """
        Publish event to all subscribers.
        
        Args:
            event: Event to publish
        """
        logger.debug(f"Publishing event: {event.event_type} for {event.project_id}")
        
        # Add to history
        self._add_to_history(event)
        
        # Collect all callbacks that should receive this event
        callbacks = []
        
        # Type-specific subscribers
        if event.event_type in self._type_subscribers:
            callbacks.extend(self._type_subscribers[event.event_type])
        
        # Project-specific subscribers
        if event.project_id in self._project_subscribers:
            callbacks.extend(self._project_subscribers[event.project_id])
        
        # Global subscribers
        callbacks.extend(self._global_subscribers)
        
        # Execute callbacks asynchronously
        tasks = []
        for callback in callbacks:
            tasks.append(self._safe_callback(callback, event))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_callback(
        self,
        callback: Callable,
        event: Event
    ) -> None:
        """
        Execute callback safely with error handling.
        
        Args:
            callback: Callback function
            event: Event to pass to callback
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            logger.error(f"Error in event callback: {e}", exc_info=True)
    
    def _add_to_history(self, event: Event) -> None:
        """Add event to history with size limit."""
        if event.project_id not in self._history:
            self._history[event.project_id] = []
        
        self._history[event.project_id].append(event)
        
        # Trim history if exceeds size limit
        if len(self._history[event.project_id]) > self._history_size:
            self._history[event.project_id] = self._history[event.project_id][-self._history_size:]
    
    def get_history(
        self,
        project_id: str,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        Get event history for a project.
        
        Args:
            project_id: Project identifier
            event_type: Optional filter by event type
            limit: Maximum events to return
        
        Returns:
            List of events (newest first)
        """
        if project_id not in self._history:
            return []
        
        events = self._history[project_id]
        
        # Filter by type if specified
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        # Return newest first, limited
        return list(reversed(events[-limit:]))
    
    def clear_history(self, project_id: str) -> None:
        """Clear event history for a project."""
        if project_id in self._history:
            del self._history[project_id]
            logger.info(f"Cleared history for project: {project_id}")


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
