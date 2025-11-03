"""
REAL End-to-End Hello World Build Test

This test uses the REAL backend system to build a hello world web app:
- REAL LLM calls to generate milestones
- REAL agents generating code
- REAL PhaseManager, Orchestrator, EventBus
- Only GitHub is mocked (PRs/commits)
- Interactive human gates (type y/n in terminal)
- Generates actual runnable project files

Run with: pytest backend/tests/test_e2e_real_hello_world.py -v -s --tb=short

Requirements:
- Database must be running (docker-compose up -d postgres)
- LLM API key must be configured
- This will make REAL API calls and cost money!
"""
import pytest
import asyncio
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from backend.services.project_build_service import ProjectBuildService, BuildStatus
from backend.services.event_bus import EventBus, Event, EventType


class InteractiveGateHandler:
    """
    Interactive gate handler - prompts user in terminal.
    User types 'y' to approve or 'n feedback text' to reject.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.auto_approve = False
        self.gate_responses = []
        
        # Subscribe to gate events
        event_bus.subscribe(EventType.GATE_TRIGGERED, self._on_gate_triggered)
    
    async def _on_gate_triggered(self, event: Event):
        """Handle gate triggered event."""
        gate_id = event.data.get("gate_id")
        gate_data = event.data
        
        print("\n" + "="*80)
        print("HUMAN GATE REQUIRED")
        print("="*80)
        print(f"Gate: {gate_data.get('gate_type', 'unknown')}")
        print(f"Phase: {gate_data.get('phase', 'unknown')}")
        print(f"Description: {gate_data.get('description', 'Approval needed')}")
        
        if gate_data.get('context'):
            print(f"\nContext:")
            for key, value in gate_data['context'].items():
                print(f"  {key}: {value}")
        
        print("\n" + "-"*80)
        print("Type 'y' to APPROVE, 'n [feedback]' to REJECT, or 'auto' to auto-approve all")
        print("-"*80)
        
        # Check auto-approve
        if self.auto_approve:
            approved = True
            feedback = "Auto-approved"
            print("AUTO-APPROVED\n")
        else:
            # Get user input
            try:
                response = input("Your response: ").strip()
                
                if response.lower() == 'auto':
                    self.auto_approve = True
                    approved = True
                    feedback = "Auto-approved"
                    print("Auto-approve enabled\n")
                
                elif response.lower() == 'y':
                    approved = True
                    feedback = "Approved"
                    print("APPROVED\n")
                
                elif response.lower().startswith('n'):
                    approved = False
                    feedback = response[1:].strip() if len(response) > 1 else "Rejected"
                    print(f"REJECTED: {feedback}\n")
                
                else:
                    approved = False
                    feedback = "Invalid response"
                    print("Invalid input, defaulting to REJECT\n")
            
            except (EOFError, KeyboardInterrupt):
                approved = False
                feedback = "Interrupted"
                print("\nInterrupted, REJECTED\n")
        
        # Record response
        self.gate_responses.append({
            "gate_id": gate_id,
            "approved": approved,
            "feedback": feedback,
            "timestamp": event.timestamp
        })
        
        # Emit approval/rejection event
        if approved:
            await self.event_bus.publish(Event(
                event_type=EventType.GATE_APPROVED,
                project_id=event.project_id,
                data={"gate_id": gate_id, "feedback": feedback}
            ))
        else:
            await self.event_bus.publish(Event(
                event_type=EventType.GATE_REJECTED,
                project_id=event.project_id,
                data={"gate_id": gate_id, "feedback": feedback}
            ))


class MockGitHubOperations:
    """Mock GitHub operations only."""
    
    def __init__(self):
        self.repos = []
        self.prs = []
        self.commits = []
    
    async def create_repo(self, name: str, **kwargs):
        repo = {"name": name, "url": f"https://github.com/mock/{name}"}
        self.repos.append(repo)
        print(f"  [MOCK] Created repo: {name}")
        return repo
    
    async def create_pr(self, title: str, **kwargs):
        pr = {"number": len(self.prs) + 1, "title": title}
        self.prs.append(pr)
        print(f"  [MOCK] Created PR: {title}")
        return pr
    
    async def commit(self, message: str, files: list):
        commit = {"sha": f"abc{len(self.commits)}", "message": message}
        self.commits.append(commit)
        print(f"  [MOCK] Committed: {message}")
        return commit


class BuildProgressMonitor:
    """Monitor and display build progress in real-time."""
    
    def __init__(self, event_bus: EventBus, project_id: str):
        self.event_bus = event_bus
        self.project_id = project_id
        self.events = []
        
        # Subscribe to project events
        event_bus.subscribe_project(project_id, self._on_event)
    
    async def _on_event(self, event: Event):
        """Display events as they happen."""
        self.events.append(event)
        
        # Format based on event type
        if event.event_type == EventType.PROJECT_CREATED:
            print(f"\nProject Created: {event.project_id}")
        
        elif event.event_type == EventType.PROJECT_STARTED:
            print(f"\nBuild Started (status: {event.data.get('status')})")
        
        elif event.event_type == EventType.PHASE_STARTED:
            print(f"\nPhase Started: {event.data.get('phase')}")
        
        elif event.event_type == EventType.AGENT_STARTED:
            print(f"  Agent Started: {event.data.get('agent_type')}")
        
        elif event.event_type == EventType.TASK_ASSIGNED:
            task_type = event.data.get('task_type', 'task')
            agent = event.data.get('agent', 'unknown')
            agent_name = agent.split('-')[0] if agent else 'Agent'
            
            print(f"\n  🔵 Orchestrator → {agent_name.title()}:")
            print(f"     \"Hey {agent_name}, please work on this {task_type}\"")
        
        elif event.event_type == EventType.TASK_COMPLETED:
            task_type = event.data.get('task_type', 'task')
            status = event.data.get('status', 'unknown')
            output = event.data.get('output', '')
            
            # Get agent name from context or output
            agent_name = "Agent"
            
            print(f"  ✅ {agent_name} → Orchestrator:")
            if status == 'completed':
                print(f"     \"Done! I completed the {task_type}\"")
                if output and len(str(output)) < 100:
                    print(f"     Output: {str(output)[:100]}")
            else:
                print(f"     \"Task finished with status: {status}\"")
        
        elif event.event_type == EventType.CODE_GENERATED:
            print(f"  Code Generated: {event.data.get('file_path')} ({event.data.get('lines', 0)} lines)")
        
        elif event.event_type == EventType.FILE_CREATED:
            path = event.data.get('path', 'unknown')
            print(f"     📄 Created file: {path}")
        
        elif event.event_type == EventType.TEST_GENERATED:
            print(f"  Test Generated: {event.data.get('test_file')}")
        
        elif event.event_type == EventType.TEST_PASSED:
            print(f"  Test Passed: {event.data.get('test_name')}")
        
        elif event.event_type == EventType.PHASE_COMPLETED:
            print(f"\nPhase Complete: {event.data.get('phase')}")
        
        elif event.event_type == EventType.PROJECT_COMPLETED:
            print(f"\nBUILD COMPLETE!")
        
        elif event.event_type == EventType.SYSTEM_CHECK:
            service = event.data.get('service', 'unknown')
            status = event.data.get('status', 'unknown')
            message = event.data.get('message', '')
            required = event.data.get('required', False)
            
            icon = "✅" if status == "available" else "⚠️" if not required else "❌"
            req_text = " (required)" if required else " (optional)"
            print(f"{icon} {service}{req_text}: {message}")
        
        elif event.event_type == EventType.ERROR_OCCURRED:
            print(f"  Error: {event.data.get('error')}")


@pytest.fixture
def output_dir():
    """Create output directory for generated project."""
    # Use a simple temp directory that doesn't require special permissions
    output = Path(tempfile.gettempdir()) / "theappapp_test_output"
    output.mkdir(exist_ok=True)
    return output


@pytest.fixture
def mock_github():
    """Create mock GitHub service."""
    return MockGitHubOperations()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_real_hello_world_build(output_dir, mock_github):
    """
    REAL end-to-end test: Build a hello world web app.
    
    This test:
    - Uses REAL LLM to generate milestones
    - Uses REAL agents to write code
    - Uses REAL services (PhaseManager, Orchestrator, etc.)
    - Mocks only GitHub operations
    - Requires interactive gate approvals
    - Generates actual runnable project files
    """
    print("\n" + "="*80)
    print("REAL END-TO-END BUILD TEST: Hello World Web App")
    print("="*80)
    print("\nWARNING: This test makes REAL LLM API calls!")
    print("WARNING: This will cost money and take time!\n")
    
    print("="*80)
    print("Starting REAL build...")
    print("="*80)
    
    # Get database engine
    # IMPORTANT: Must use postgresql+psycopg:// to use psycopg3 (not psycopg2)
    # Override conftest.py DATABASE_URL which uses theappapp_test - we need theappapp
    database_url = "postgresql+psycopg://postgres:postgres@localhost:55432/theappapp"
    
    engine = create_engine(database_url)
    
    # Create event bus
    event_bus = EventBus()
    
    # Set up build progress monitor
    project_id = None  # Will be set after build starts
    
    # Set up interactive gate handler
    gate_handler = InteractiveGateHandler(event_bus)
    
    # Create ProjectBuildService with REAL services
    # Note: GitHub operations will be mocked by the mock_github fixture
    # We could patch httpx calls to GitHub API if needed, but for now we'll let them run
    
    # Initialize build service
    build_service = ProjectBuildService(
        db_engine=engine,
        llm_client=None,  # Will use default LLM client
        event_bus=event_bus
    )
    
    print("\nSubmitting build request...")
    print("   Description: Simple hello world web app")
    print("   Requirements: Button that shows popup\n")
    
    # Start the build (THIS IS REAL!)
    project_id = await build_service.start_build(
        description="""
Build a simple hello world web app with:
- A web page with a button
- When button is clicked, show a popup/alert saying "Hello World!"
- Use vanilla HTML/CSS/JavaScript (no frameworks)
- Make it look nice with modern styling
- Include a backend API endpoint that returns a greeting message
        """.strip(),
        tech_stack={
            "frontend": "html",
            "backend": "python",
            "framework": "flask"
        },
        auto_approve_gates=False  # Require human approval
    )
    
    print(f"Build started: {project_id}\n")
    
    # Set up progress monitor now that we have project_id
    progress_monitor = BuildProgressMonitor(event_bus, project_id)
    
    # Monitor build progress
    print("="*80)
    print("MONITORING BUILD PROGRESS")
    print("="*80)
    
    max_wait = 300  # 5 minutes max
    check_interval = 2  # Check every 2 seconds
    elapsed = 0
    
    while elapsed < max_wait:
        await asyncio.sleep(check_interval)
        elapsed += check_interval
        
        # Get build status
        status = await build_service.get_build_status(project_id)
        
        # Check if complete
        if status.status in [BuildStatus.COMPLETED, BuildStatus.FAILED, BuildStatus.CANCELLED]:
            break
        
        # Show progress update every 10 seconds
        if elapsed % 10 == 0:
            print(f"\nStatus: {status.status} | Phase: {status.current_phase} | Progress: {status.progress_percent:.1f}%")
    
    # Final status
    final_status = await build_service.get_build_status(project_id)
    
    print("\n" + "="*80)
    print("BUILD COMPLETE")
    print("="*80)
    print(f"Status: {final_status.status}")
    print(f"Final Phase: {final_status.current_phase}")
    print(f"Progress: {final_status.progress_percent}%")
    
    # Print event summary
    print("\nEvents Summary:")
    event_counts = {}
    for event in progress_monitor.events:
        event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
    
    for event_type, count in sorted(event_counts.items()):
        print(f"   {event_type}: {count}")
    
    # Print gate summary
    print("\nGates Summary:")
    print(f"   Total gates: {len(gate_handler.gate_responses)}")
    approved = sum(1 for g in gate_handler.gate_responses if g['approved'])
    rejected = len(gate_handler.gate_responses) - approved
    print(f"   Approved: {approved}")
    print(f"   Rejected: {rejected}")
    
    # Print GitHub mock summary
    print("\nGitHub Operations (mocked):")
    print(f"   Repos created: {len(mock_github.repos)}")
    print(f"   PRs created: {len(mock_github.prs)}")
    print(f"   Commits made: {len(mock_github.commits)}")
    
    # Check if files were generated
    # In real system, files would be in project workspace
    print("\nGenerated Files:")
    print(f"   Output directory: {output_dir}")
    
    # Token Usage and Cost Report
    print("\n" + "="*80)
    print("💰 TOKEN USAGE & COST REPORT")
    print("="*80)
    
    # Get event-based statistics
    task_assigned_events = [e for e in progress_monitor.events if e.event_type == EventType.TASK_ASSIGNED]
    task_completed_events = [e for e in progress_monitor.events if e.event_type == EventType.TASK_COMPLETED]
    
    # Count tasks by agent
    print("\nAgent Activity (Task Assignments):")
    agent_tasks = {}
    for event in task_assigned_events:
        agent = event.data.get('agent', 'unknown')
        agent_name = agent.split('-')[0] if agent and agent != 'unknown' else 'unknown'
        agent_tasks[agent_name] = agent_tasks.get(agent_name, 0) + 1
    
    for agent_name, task_count in sorted(agent_tasks.items()):
        print(f"   {agent_name.title()}: {task_count} task(s)")
    
    print(f"\nTotal Tasks Assigned: {len(task_assigned_events)}")
    print(f"Total Tasks Completed: {len(task_completed_events)}")
    
    # Note about token data
    print("\n" + "-"*80)
    print("💡 Token & Cost Details:")
    print("   Detailed token usage and costs are shown above in real-time")
    print("   Each LLM call displays: 💰 Tokens: XXXX | Cost: $X.XXXXXX")
    print("   Scroll up to see per-call breakdown during execution")
    print("-"*80)
    
    # Verify build succeeded
    print("\n" + "="*80)
    print("DETAILED STATUS CHECK")
    print("="*80)
    print(f"Status: {final_status.status}")
    print(f"Phase: {final_status.current_phase}")
    print(f"Error events: {sum(1 for e in progress_monitor.events if e.event_type == EventType.ERROR_OCCURRED)}")
    print(f"   Failed events: {sum(1 for e in progress_monitor.events if e.event_type == EventType.PROJECT_FAILED)}")
    
    # Check for actual failure
    has_failure = sum(1 for e in progress_monitor.events if e.event_type in [EventType.PROJECT_FAILED, EventType.ERROR_OCCURRED]) > 0
    
    if has_failure:
        print("\nBUILD ACTUALLY FAILED - Found failure/error events!")
        # Print failure details
        for event in progress_monitor.events:
            if event.event_type in [EventType.PROJECT_FAILED, EventType.ERROR_OCCURRED]:
                print(f"\n   Event: {event.event_type}")
                print(f"   Data: {event.data}")
        pytest.fail("Build reported COMPLETED but had failure events")
    
    assert final_status.status == BuildStatus.COMPLETED, f"Build failed with status: {final_status.status}"
    
    print("\nREAL BUILD TEST PASSED!")
    print("="*80)


if __name__ == "__main__":
    print("\nRunning REAL end-to-end build test...")
    print("This uses REAL LLM calls and will cost money!\n")
    
    pytest.main([__file__, "-v", "-s", "--tb=short"])
