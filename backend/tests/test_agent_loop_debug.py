"""
Debug test to diagnose agent loop behavior.
Runs exactly 2 iterations then stops and reports.
"""
import asyncio
from collections import Counter

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine

from backend.services.event_bus import Event, EventType, get_event_bus
from backend.services.project_build_service import ProjectBuildService

load_dotenv()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_agent_loop_debug():
    """
    DEBUG TEST: Run agent for exactly 2 actions, then stop and report.
    
    This helps us see:
    - What actions the agent takes
    - If self-assessment is being called
    - What the results are
    - Why the loop continues
    """
    print("\n" + "="*80)
    print("AGENT LOOP DEBUG TEST")
    print("="*80)
    print("\nThis test will:")
    print("1. Start a build")
    print("2. Let agent take 2 actions")  
    print("3. Force stop")
    print("4. Report what happened\n")
    print("\n⚠️  NOTE: This test will fail due to DB schema issues")
    print("   BUT it will still show diagnostic output!\n")
    
    # Database setup (same as real test)
    database_url = "postgresql+psycopg://postgres:postgres@127.0.0.1:55432/theappapp"
    engine = create_engine(database_url)
    
    # Create build service
    build_service = ProjectBuildService(db_engine=engine, llm_client=None)
    
    # Subscribe to ALL events
    event_bus = get_event_bus()
    events_captured = []
    
    async def capture_event(event: Event):
        events_captured.append(event)
        print(f"📝 Event: {event.event_type.value} - {event.data.get('description', '')[:50]}")
    
    # Subscribe to all event types
    for event_type in EventType:
        event_bus.subscribe(event_type, capture_event)
    
    # Start build
    project_desc = """Simple hello world web app with:
- A web page with a button
- When button is clicked, show a popup/alert saying "Hello World!"
- Use vanilla HTML/CSS/JavaScript (no frameworks)
"""
    
    print("\n" + "="*80)
    print("STARTING BUILD")
    print("="*80)
    
    # Start build in background
    build_task = asyncio.create_task(
        build_service.start_build(
            description=project_desc,
            tech_stack={"frontend": "HTML/JS", "backend": "Python"}
        )
    )
    
    # Wait for agent to start
    await asyncio.sleep(2)
    
    # Let it run for 2 LLM calls worth of time (~10 seconds)
    print("\n⏱️  Letting agent run for 10 seconds...")
    await asyncio.sleep(10)
    
    # FORCE STOP
    print("\n🛑 FORCE STOPPING BUILD\n")
    build_task.cancel()
    
    try:
        await build_task
    except asyncio.CancelledError:
        print("✅ Build cancelled successfully\n")
    except Exception as e:
        print(f"⚠️  Build failed (expected for this debug test): {type(e).__name__}\n")
        print(f"   Error: {str(e)[:100]}\n")
    
    # GENERATE REPORT
    print("\n" + "="*80)
    print("DIAGNOSTIC REPORT")
    print("="*80)
    
    # Count event types
    event_counts = Counter(e.event_type.value for e in events_captured)
    
    print("\n📊 Event Summary:")
    for event_type, count in sorted(event_counts.items()):
        print(f"  {event_type}: {count}")
    
    # Find task/action events
    task_events = [e for e in events_captured if 'TASK' in e.event_type.value]
    agent_events = [e for e in events_captured if 'AGENT' in e.event_type.value]
    
    print(f"\n🔵 Task Events: {len(task_events)}")
    for event in task_events:
        print(f"  - {event.event_type.value}: {event.data}")
    
    print(f"\n🤖 Agent Events: {len(agent_events)}")
    for event in agent_events:
        print(f"  - {event.event_type.value}: {event.data}")
    
    # Check for self-assessment logs
    # (These would be in agent logs, not events)
    print("\n" + "="*80)
    print("ANALYSIS")
    print("="*80)
    
    task_assigned = len([e for e in events_captured if e.event_type == EventType.TASK_ASSIGNED])
    task_completed = len([e for e in events_captured if e.event_type == EventType.TASK_COMPLETED])
    
    print(f"\n📌 Tasks Assigned: {task_assigned}")
    print(f"✅ Tasks Completed: {task_completed}")
    
    if task_assigned > task_completed:
        print(f"\n⚠️  ISSUE DETECTED: {task_assigned - task_completed} tasks started but not completed")
        print("   This suggests the agent loop is running but not exiting")
    
    if task_assigned > 1:
        print(f"\n⚠️  ISSUE DETECTED: Multiple tasks assigned ({task_assigned})")
        print("   Expected: 1 task (workshopper writes requirements.md)")
        print("   Actual: Task may be getting re-queued or duplicated")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\nTo debug further:")
    print("1. Check logs above for '🔍 Self-assessment result'")
    print("2. Look for 'Self-assessment failed' errors")
    print("3. Count how many times 'Plan the next action' appears")
    print("4. Check if same task_id appears multiple times")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    
    # The test "passes" regardless - we just want the diagnostic output
    assert True, "Debug test complete - review output above"
