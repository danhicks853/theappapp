"""
Progress Reporter Service

Generates LLM-powered progress reports and status updates for projects.
Provides daily summaries, phase reports, and blocker identification.

Reference: Phase 3.1 - Phase Management System
"""
import logging
from typing import Optional, List, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class Report:
    """Progress report data model."""
    id: str
    project_id: str
    report_type: str  # 'daily', 'phase_summary', 'blockers'
    title: str
    summary: str
    completed_tasks: List[str]
    pending_tasks: List[str]
    blockers: List[str]
    test_coverage: Optional[float]
    next_steps: List[str]
    timeline_status: str  # 'on_track', 'at_risk', 'delayed'
    generated_at: str
    period_start: Optional[str]
    period_end: Optional[str]


class ProgressReporter:
    """
    Service for generating progress reports with LLM assistance.
    
    Features:
    - Daily progress summaries
    - Phase completion reports
    - Blocker identification and reporting
    - Timeline status analysis
    
    Example:
        reporter = ProgressReporter(engine, llm_client)
        daily = await reporter.generate_daily_report("proj-123")
        phase_report = await reporter.generate_phase_summary("phase-123")
        blockers = await reporter.generate_blockers_report("proj-123")
    """
    
    def __init__(self, engine: Engine, llm_client: Optional[Any] = None):
        """
        Initialize progress reporter.
        
        Args:
            engine: Database engine
            llm_client: Optional LLM client for natural language generation
        """
        self.engine = engine
        self.llm_client = llm_client
        logger.info("ProgressReporter initialized")
    
    async def generate_daily_report(
        self,
        project_id: str
    ) -> Report:
        """
        Generate daily progress summary for a project.
        
        Args:
            project_id: Project identifier
        
        Returns:
            Daily progress report
        """
        logger.info(f"Generating daily report for project: {project_id}")
        
        report_id = self._generate_report_id()
        now = datetime.utcnow()
        period_start = (now - timedelta(days=1)).isoformat()
        period_end = now.isoformat()
        
        # Gather progress data
        completed_tasks = await self._get_completed_tasks(project_id, days=1)
        pending_tasks = await self._get_pending_tasks(project_id)
        blockers = await self._identify_blockers(project_id)
        test_coverage = await self._get_test_coverage(project_id)
        next_steps = await self._get_next_steps(project_id)
        timeline_status = await self._assess_timeline(project_id)
        
        # Generate summary
        if self.llm_client:
            summary = await self._generate_llm_summary(
                report_type="daily",
                completed_tasks=completed_tasks,
                pending_tasks=pending_tasks,
                blockers=blockers,
                test_coverage=test_coverage
            )
        else:
            summary = self._generate_basic_summary(
                completed_count=len(completed_tasks),
                pending_count=len(pending_tasks),
                blocker_count=len(blockers),
                test_coverage=test_coverage
            )
        
        report = Report(
            id=report_id,
            project_id=project_id,
            report_type="daily",
            title=f"Daily Progress Report - {now.strftime('%Y-%m-%d')}",
            summary=summary,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            blockers=blockers,
            test_coverage=test_coverage,
            next_steps=next_steps,
            timeline_status=timeline_status,
            generated_at=now.isoformat(),
            period_start=period_start,
            period_end=period_end
        )
        
        # Store report
        await self._store_report(report)
        
        logger.info(f"Daily report generated: {report_id}")
        return report
    
    async def generate_phase_summary(
        self,
        phase_id: str
    ) -> Report:
        """
        Generate phase completion summary.
        
        Args:
            phase_id: Phase identifier
        
        Returns:
            Phase summary report
        """
        logger.info(f"Generating phase summary for phase: {phase_id}")
        
        report_id = self._generate_report_id()
        now = datetime.utcnow()
        
        # Get phase info
        from backend.services.phase_manager import PhaseManager
        phase_mgr = PhaseManager(self.engine)
        phase = await phase_mgr.get_phase(phase_id)
        
        if not phase:
            raise ValueError(f"Phase not found: {phase_id}")
        
        # Get deliverables
        from backend.services.deliverable_tracker import DeliverableTracker
        tracker = DeliverableTracker(self.engine)
        deliverables = await tracker.get_phase_deliverables(phase_id)
        
        completed_deliverables = [
            d.name for d in deliverables
            if d.status.value in ['completed', 'validated']
        ]
        
        pending_deliverables = [
            d.name for d in deliverables
            if d.status.value not in ['completed', 'validated']
        ]
        
        # Get phase completeness
        completeness = await tracker.get_phase_completeness(phase_id)
        
        # Generate summary
        summary = (
            f"Phase {phase.phase_name.value} is {completeness:.0%} complete. "
            f"Completed {len(completed_deliverables)} of {len(deliverables)} deliverables. "
        )
        
        if completeness >= 1.0:
            summary += "Phase ready for completion."
        elif completeness >= 0.75:
            summary += "Phase nearing completion."
        else:
            summary += f"{len(pending_deliverables)} deliverables still in progress."
        
        report = Report(
            id=report_id,
            project_id=phase.project_id,
            report_type="phase_summary",
            title=f"Phase Summary - {phase.phase_name.value.title()}",
            summary=summary,
            completed_tasks=completed_deliverables,
            pending_tasks=pending_deliverables,
            blockers=[],
            test_coverage=None,
            next_steps=pending_deliverables[:5],
            timeline_status="on_track" if completeness >= 0.75 else "at_risk",
            generated_at=now.isoformat(),
            period_start=phase.started_at,
            period_end=phase.completed_at if phase.completed_at else now.isoformat()
        )
        
        await self._store_report(report)
        
        logger.info(f"Phase summary generated: {report_id}")
        return report
    
    async def generate_blockers_report(
        self,
        project_id: str
    ) -> Report:
        """
        Generate report focused on current blockers and issues.
        
        Args:
            project_id: Project identifier
        
        Returns:
            Blockers report
        """
        logger.info(f"Generating blockers report for project: {project_id}")
        
        report_id = self._generate_report_id()
        now = datetime.utcnow()
        
        # Identify all blockers
        blockers = await self._identify_blockers(project_id)
        
        # Get pending gates
        gate_blockers = await self._get_pending_gates(project_id)
        
        # Combine all blockers
        all_blockers = blockers + [f"Pending gate: {g}" for g in gate_blockers]
        
        # Generate summary
        if all_blockers:
            summary = (
                f"Found {len(all_blockers)} blockers preventing progress. "
                "Immediate action required to resolve these issues."
            )
            timeline_status = "delayed"
            next_steps = [f"Resolve: {b}" for b in all_blockers[:5]]
        else:
            summary = "No blockers identified. Project progressing smoothly."
            timeline_status = "on_track"
            next_steps = ["Continue with planned tasks"]
        
        report = Report(
            id=report_id,
            project_id=project_id,
            report_type="blockers",
            title=f"Blockers Report - {now.strftime('%Y-%m-%d')}",
            summary=summary,
            completed_tasks=[],
            pending_tasks=[],
            blockers=all_blockers,
            test_coverage=None,
            next_steps=next_steps,
            timeline_status=timeline_status,
            generated_at=now.isoformat(),
            period_start=None,
            period_end=None
        )
        
        await self._store_report(report)
        
        logger.info(f"Blockers report generated: {report_id} ({len(all_blockers)} blockers)")
        return report
    
    async def _get_completed_tasks(self, project_id: str, days: int = 1) -> List[str]:
        """Get tasks completed in the last N days."""
        # TODO: Implement task tracking
        # For now, return deliverables marked complete recently
        return []
    
    async def _get_pending_tasks(self, project_id: str) -> List[str]:
        """Get tasks still pending."""
        # TODO: Implement task tracking
        return []
    
    async def _identify_blockers(self, project_id: str) -> List[str]:
        """Identify current blockers for the project."""
        blockers = []
        
        # Check for failed tests
        # TODO: Implement test status checking
        
        # Check for incomplete deliverables past deadline
        # TODO: Implement deadline tracking
        
        # Check for blocked phases
        from backend.services.phase_manager import PhaseManager, PhaseStatus
        phase_mgr = PhaseManager(self.engine)
        phases = await phase_mgr.get_phase_history(project_id)
        
        for phase in phases:
            if phase.status == PhaseStatus.BLOCKED:
                blockers.append(f"Phase {phase.phase_name.value} is blocked")
        
        return blockers
    
    async def _get_pending_gates(self, project_id: str) -> List[str]:
        """Get pending approval gates."""
        # TODO: Integrate with GateManager
        return []
    
    async def _get_test_coverage(self, project_id: str) -> Optional[float]:
        """Get current test coverage percentage."""
        # TODO: Implement coverage tracking
        # For now, try to get from validator
        try:
            from backend.services.phase_validator import PhaseValidator
            validator = PhaseValidator(self.engine)
            coverage = await validator._get_coverage()
            return coverage if coverage > 0 else None
        except Exception as e:
            logger.warning(f"Could not get test coverage: {e}")
            return None
    
    async def _get_next_steps(self, project_id: str) -> List[str]:
        """Get next steps for the project."""
        # Get current phase and its pending deliverables
        from backend.services.phase_manager import PhaseManager
        phase_mgr = PhaseManager(self.engine)
        current_phase = await phase_mgr.get_current_phase(project_id)
        
        if not current_phase:
            return ["Start workshopping phase"]
        
        from backend.services.deliverable_tracker import DeliverableTracker
        tracker = DeliverableTracker(self.engine)
        deliverables = await tracker.get_phase_deliverables(current_phase.id)
        
        pending = [
            d.name for d in deliverables
            if d.status.value not in ['completed', 'validated']
        ]
        
        return pending[:5] if pending else ["Complete phase and transition to next"]
    
    async def _assess_timeline(self, project_id: str) -> str:
        """Assess timeline status."""
        # TODO: Implement timeline tracking with estimates
        # For now, base on blockers
        blockers = await self._identify_blockers(project_id)
        
        if blockers:
            return "at_risk"
        return "on_track"
    
    async def _generate_llm_summary(
        self,
        report_type: str,
        **kwargs
    ) -> str:
        """Generate natural language summary using LLM."""
        # TODO: Implement LLM-based summary generation
        logger.info("LLM summary generation not yet implemented")
        return self._generate_basic_summary(**kwargs)
    
    def _generate_basic_summary(
        self,
        completed_count: int = 0,
        pending_count: int = 0,
        blocker_count: int = 0,
        test_coverage: Optional[float] = None
    ) -> str:
        """Generate basic summary without LLM."""
        parts = []
        
        if completed_count > 0:
            parts.append(f"Completed {completed_count} tasks")
        
        if pending_count > 0:
            parts.append(f"{pending_count} tasks pending")
        
        if blocker_count > 0:
            parts.append(f"{blocker_count} blockers identified")
        
        if test_coverage is not None:
            parts.append(f"Test coverage: {test_coverage:.1f}%")
        
        return ". ".join(parts) + "." if parts else "No progress data available."
    
    async def _store_report(self, report: Report) -> None:
        """Store report in database."""
        import json
        
        query = text("""
            INSERT INTO progress_reports
            (id, project_id, report_type, title, summary, completed_tasks,
             pending_tasks, blockers, test_coverage, next_steps, timeline_status,
             generated_at, period_start, period_end, created_at)
            VALUES (:id, :project_id, :report_type, :title, :summary, :completed_tasks,
                    :pending_tasks, :blockers, :test_coverage, :next_steps,
                    :timeline_status, :generated_at, :period_start, :period_end, NOW())
        """)
        
        with self.engine.connect() as conn:
            conn.execute(query, {
                "id": report.id,
                "project_id": report.project_id,
                "report_type": report.report_type,
                "title": report.title,
                "summary": report.summary,
                "completed_tasks": json.dumps(report.completed_tasks) if report.completed_tasks else None,
                "pending_tasks": json.dumps(report.pending_tasks) if report.pending_tasks else None,
                "blockers": json.dumps(report.blockers) if report.blockers else None,
                "test_coverage": report.test_coverage,
                "next_steps": json.dumps(report.next_steps) if report.next_steps else None,
                "timeline_status": report.timeline_status,
                "generated_at": report.generated_at,
                "period_start": report.period_start,
                "period_end": report.period_end
            })
            conn.commit()
        
        logger.debug(f"Report stored: {report.id}")
    
    async def get_recent_reports(
        self,
        project_id: str,
        report_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Report]:
        """Get recent reports for a project."""
        if report_type:
            query = text("""
                SELECT id, project_id, report_type, title, summary, completed_tasks,
                       pending_tasks, blockers, test_coverage, next_steps, timeline_status,
                       generated_at, period_start, period_end
                FROM progress_reports
                WHERE project_id = :project_id AND report_type = :report_type
                ORDER BY generated_at DESC
                LIMIT :limit
            """)
            params = {"project_id": project_id, "report_type": report_type, "limit": limit}
        else:
            query = text("""
                SELECT id, project_id, report_type, title, summary, completed_tasks,
                       pending_tasks, blockers, test_coverage, next_steps, timeline_status,
                       generated_at, period_start, period_end
                FROM progress_reports
                WHERE project_id = :project_id
                ORDER BY generated_at DESC
                LIMIT :limit
            """)
            params = {"project_id": project_id, "limit": limit}
        
        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            rows = result.fetchall()
            
            reports = [
                Report(
                    id=str(row[0]),
                    project_id=str(row[1]),
                    report_type=row[2],
                    title=row[3],
                    summary=row[4],
                    completed_tasks=row[5] or [],
                    pending_tasks=row[6] or [],
                    blockers=row[7] or [],
                    test_coverage=row[8],
                    next_steps=row[9] or [],
                    timeline_status=row[10],
                    generated_at=row[11],
                    period_start=row[12],
                    period_end=row[13]
                )
                for row in rows
            ]
            
            return reports
    
    def _generate_report_id(self) -> str:
        """Generate unique report ID."""
        import uuid
        return f"report-{uuid.uuid4()}"
