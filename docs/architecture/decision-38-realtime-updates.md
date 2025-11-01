# Decision 38: Real-time Updates

## Status
✅ RESOLVED | Date: Oct 31, 2025 | Priority: P0

## Decision
**Choice**: WebSockets (no alternative viable)

**Implementation**: WebSocket connection for live agent activity, file directory contents, project status changes, approval requests

**Fallback**: Polling if WebSocket fails

**Use Cases**: Real-time agent monitoring, live file system updates, instant approval notifications

## Related
- Decision 73: Frontend-Backend API (WebSocket specification)
