"""
Test to diagnose deliverable completion loop issue.

This test focuses specifically on:
1. Orchestrator assigns task to workshopper
2. Workshopper completes task
3. Orchestrator marks deliverable complete
4. Verify deliverable is NOT re-queued
"""
import uuid

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from backend.agents.workshopper_agent import WorkshopperAgent
from backend.services.event_bus import get_event_bus
from backend.services.orchestrator import AgentType, Orchestrator, Task, TaskStatus
from backend.services.phase_manager import PhaseManager
from backend.services.task_executor import TaskExecutor
from backend.services.tool_access_service import ToolAccessService

load_dotenv()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_deliverable_completion_no_loop():
    """
    Test that a completed deliverable is NOT re-queued.
    
    Flow:
    1. Create orchestrator + phase manager + task executor
    2. Create one deliverable
    3. Assign task to workshopper
    4. Workshopper completes
    5. Check: Deliverable should be marked complete in DB
    6. Check: Same deliverable should NOT be in pending list
    """
    print("\n" + "="*80)
    print("DELIVERABLE COMPLETION LOOP TEST")
    print("="*80)
    print("\nObjective: Verify deliverable marked complete doesn't get re-queued\n")
    
    # Database setup
    database_url = "postgresql+psycopg://postgres:postgres@127.0.0.1:55432/theappapp"
    engine = create_engine(database_url)
    
    # Create unique project ID for this test (must be valid UUID without prefix)
    project_id = str(uuid.uuid4())
    
    # Clean up any existing data for this project
    print("🧹 Cleaning up old test data...")
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM deliverables WHERE project_id = :pid"), {"pid": project_id})
        conn.execute(text("DELETE FROM phases WHERE project_id = :pid"), {"pid": project_id})
        conn.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": project_id})
        conn.commit()
    
    print("✅ Cleanup complete\n")
    
    # Initialize phase manager
    print("📋 Initializing phase manager...")
    phase_manager = PhaseManager(engine=engine, project_id=project_id)
    
    # Start the phase manually
    from backend.services.phase_manager import PhaseType
    await phase_manager.start_phase(project_id, PhaseType.WORKSHOPPING)
    current_phase = await phase_manager.get_current_phase(project_id)
    
    # Create a single deliverable directly
    print("📝 Creating single deliverable...")
    deliverable_id = f"deliv-{uuid.uuid4()}"
    
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO deliverables (
                id, phase_id, project_id, deliverable_type, 
                title, name, description, status, created_at
            ) VALUES (
                :id, :phase_id, :project_id, :type,
                :title, :name, :description, 'not_started', NOW()
            )
        """), {
            "id": deliverable_id,
            "phase_id": str(current_phase.id),
            "project_id": project_id,
            "type": "document",
            "title": "requirements.md",
            "name": "requirements.md",
            "description": "Requirements document"
        })
        conn.commit()
    
    print(f"✅ Deliverable created: {deliverable_id}\n")
    
    # Verify the deliverable was created
    pending_deliverables = await phase_manager.get_pending_deliverables()
    print(f"📦 Pending deliverables: {len(pending_deliverables)}")
    
    if len(pending_deliverables) != 1:
        pytest.fail(f"Expected 1 deliverable, got {len(pending_deliverables)}")
    
    deliverable = pending_deliverables[0]
    print(f"   Deliverable ID: {deliverable['id']}")
    print(f"   Title: {deliverable.get('title', 'N/A')}")
    print(f"   Matches created ID: {deliverable['id'] == deliverable_id}\n")
    
    # Create orchestrator
    print("🎭 Creating orchestrator...")
    tas_client = ToolAccessService(db_session=None, use_db=False)
    orchestrator = Orchestrator(
        project_id=project_id,
        llm_client=None,  # Will create a real one
        tas_client=tas_client
    )
    print("✅ Orchestrator created\n")
    
    # Create task executor with phase_manager
    print("⚙️  Creating task executor...")
    event_bus = get_event_bus()
    task_executor = TaskExecutor(
        orchestrator=orchestrator,
        event_bus=event_bus,
        max_workers=1,
        phase_manager=phase_manager
    )
    print(f"✅ Task executor created (phase_manager={'present' if task_executor.phase_manager else 'MISSING'})\n")
    
    # Create and register workshopper agent
    print("👷 Creating workshopper agent...")
    from backend.services.agent_llm_client import AgentLLMClient
    from backend.services.openai_adapter import OpenAIAdapter
    import os
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")
    
    openai_adapter = OpenAIAdapter(api_key=api_key)
    llm_client = AgentLLMClient(openai_adapter)
    
    workshopper = WorkshopperAgent(
        agent_id="test-workshopper",
        orchestrator=orchestrator,
        llm_client=llm_client
    )
    task_executor.register_agent_instance("test-workshopper", workshopper)
    print("✅ Workshopper registered\n")
    
    # Create task from deliverable
    print("📝 Creating task...")
    task = Task(
        task_id=deliverable_id,
        task_type="workshopping",
        agent_type=AgentType.WORKSHOPPER,
        payload={
            "id": deliverable_id,
            "goal": "Write comprehensive requirements.md with user stories",
            "project_id": project_id
        },
        project_id=project_id,
        status=TaskStatus.PENDING
    )
    print(f"✅ Task created: {task.task_id}\n")
    
    print("="*80)
    print("EXECUTING TASK")
    print("="*80 + "\n")
    
    # Execute task directly (bypass queue for test)
    print("🏃 Agent starting execution...\n")
    result = await workshopper.run_task(task)
    
    print("\n" + "="*80)
    print("TASK EXECUTION COMPLETE")
    print("="*80)
    print(f"\n✅ Agent returned")
    print(f"   Success: {result.success}")
    print(f"   Steps: {len(result.steps)}")
    print(f"   Errors: {len(result.errors)}\n")
    
    # Now mark it complete via task executor (simulating what orchestrator does)
    print("="*80)
    print("MARKING DELIVERABLE COMPLETE")
    print("="*80 + "\n")
    
    await task_executor._handle_task_result(task, result)
    
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80 + "\n")
    
    # Check deliverable status in DB
    print("🔍 Checking deliverable status in database...")
    pending_after = await phase_manager.get_pending_deliverables()
    
    print(f"   Pending deliverables BEFORE: 1")
    print(f"   Pending deliverables AFTER:  {len(pending_after)}\n")
    
    # Check if our deliverable is still pending
    still_pending = any(d["id"] == deliverable_id for d in pending_after)
    
    print("="*80)
    print("TEST RESULTS")
    print("="*80 + "\n")
    
    if still_pending:
        print("❌ FAILED: Deliverable is still PENDING")
        print(f"   Deliverable {deliverable_id} was NOT marked complete in database!")
        print(f"   This will cause the infinite loop!")
        
        # Show what deliverables are still pending
        print(f"\n   Still pending:")
        for d in pending_after:
            print(f"     - {d['id']}: {d.get('title', 'N/A')}")
        
        pytest.fail(f"Deliverable {deliverable_id} still pending after completion!")
    else:
        print("✅ SUCCESS: Deliverable is NO LONGER pending")
        print(f"   Deliverable {deliverable_id} was marked complete in database!")
        print(f"   No infinite loop will occur!")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    
    assert not still_pending, "Deliverable should not be pending after completion"
    assert result.success, "Task should complete successfully"
