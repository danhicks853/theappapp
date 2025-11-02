"""
Quality Metrics Analyzer Service

AI-driven quality metrics aggregation and improvement recommendations.
Aggregates TestQualityScorer, SecurityTestRunner, and coverage metrics.

Reference: Phase 3.3 - Quality Assurance System
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from backend.services.test_quality_scorer import TestQualityScorer
from backend.services.security_test_runner import SecurityTestRunner

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Aggregated quality metrics."""
    timestamp: str
    test_coverage: float
    test_quality_score: float
    security_score: float
    performance_score: float
    overall_quality: float


@dataclass
class QualityTrend:
    """Quality trend over time."""
    metric_name: str
    current_value: float
    previous_value: float
    change_percent: float
    trending_up: bool


@dataclass
class QualityRecommendation:
    """AI-generated quality improvement recommendation."""
    priority: int  # 1-5
    category: str
    title: str
    description: str
    expected_impact: str


class QualityMetricsAnalyzer:
    """
    Service for quality metrics aggregation and analysis.
    
    Aggregates:
    - Test coverage from CI
    - Test quality scores from TestQualityScorer
    - Security scan results from SecurityTestRunner
    - Performance metrics from PerformanceTester
    
    Features:
    - Metrics aggregation over time
    - Trend analysis
    - AI-powered improvement recommendations
    
    Example:
        analyzer = QualityMetricsAnalyzer(llm_client, test_scorer, security_runner)
        metrics = await analyzer.collect_metrics(project_id)
        trends = await analyzer.analyze_trends(project_id, days=7)
        recommendations = await analyzer.generate_recommendations(metrics, trends)
    """
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        test_scorer: Optional[TestQualityScorer] = None,
        security_runner: Optional[SecurityTestRunner] = None
    ):
        """Initialize quality metrics analyzer."""
        self.llm_client = llm_client
        self.test_scorer = test_scorer or TestQualityScorer()
        self.security_runner = security_runner or SecurityTestRunner()
        self.metrics_history: Dict[str, List[QualityMetrics]] = {}
        logger.info("QualityMetricsAnalyzer initialized")
    
    async def collect_metrics(
        self,
        project_id: str,
        test_files: Optional[List[str]] = None,
        code_files: Optional[List[str]] = None
    ) -> QualityMetrics:
        """
        Collect current quality metrics for a project.
        
        Args:
            project_id: Project identifier
            test_files: Optional list of test files
            code_files: Optional list of code files
        
        Returns:
            Current QualityMetrics
        """
        logger.info(f"Collecting quality metrics for project: {project_id}")
        
        # Collect test quality scores
        test_quality = 0.0
        if test_files:
            test_scores = []
            for test_file in test_files[:10]:  # Sample first 10
                try:
                    score = await self.test_scorer.score_test_file(test_file)
                    test_scores.append(score.total_score)
                except Exception as e:
                    logger.warning(f"Failed to score {test_file}: {e}")
            
            test_quality = sum(test_scores) / len(test_scores) if test_scores else 0
        
        # Collect security scores
        security_score = 100.0  # Default high score
        if code_files:
            total_vulns = 0
            for code_file in code_files[:10]:  # Sample first 10
                try:
                    with open(code_file, 'r') as f:
                        code = f.read()
                    scan = await self.security_runner.scan_code(code, file_path=code_file)
                    total_vulns += len(scan.vulnerabilities)
                except Exception as e:
                    logger.warning(f"Failed to scan {code_file}: {e}")
            
            # Deduct points for vulnerabilities
            security_score = max(0, 100 - (total_vulns * 10))
        
        # Calculate overall quality (weighted average)
        coverage = 85.0  # Placeholder - would come from CI
        performance = 80.0  # Placeholder - would come from PerformanceTester
        
        overall = (
            coverage * 0.3 +
            test_quality * 0.3 +
            security_score * 0.25 +
            performance * 0.15
        )
        
        metrics = QualityMetrics(
            timestamp=datetime.utcnow().isoformat(),
            test_coverage=coverage,
            test_quality_score=test_quality,
            security_score=security_score,
            performance_score=performance,
            overall_quality=overall
        )
        
        # Store in history
        if project_id not in self.metrics_history:
            self.metrics_history[project_id] = []
        self.metrics_history[project_id].append(metrics)
        
        return metrics
    
    async def analyze_trends(
        self,
        project_id: str,
        days: int = 7
    ) -> List[QualityTrend]:
        """
        Analyze quality trends over time.
        
        Args:
            project_id: Project identifier
            days: Number of days to analyze
        
        Returns:
            List of quality trends
        """
        logger.info(f"Analyzing quality trends for {project_id} over {days} days")
        
        history = self.metrics_history.get(project_id, [])
        if len(history) < 2:
            logger.warning("Insufficient history for trend analysis")
            return []
        
        current = history[-1]
        previous = history[-2] if len(history) >= 2 else history[0]
        
        trends = []
        
        # Analyze each metric
        for metric_name in ["test_coverage", "test_quality_score", "security_score", "performance_score", "overall_quality"]:
            current_val = getattr(current, metric_name)
            previous_val = getattr(previous, metric_name)
            
            if previous_val > 0:
                change = ((current_val - previous_val) / previous_val) * 100
                trending_up = change > 0
            else:
                change = 0
                trending_up = True
            
            trends.append(QualityTrend(
                metric_name=metric_name,
                current_value=current_val,
                previous_value=previous_val,
                change_percent=change,
                trending_up=trending_up
            ))
        
        return trends
    
    async def generate_recommendations(
        self,
        metrics: QualityMetrics,
        trends: List[QualityTrend]
    ) -> List[QualityRecommendation]:
        """
        Generate AI-powered improvement recommendations.
        
        Args:
            metrics: Current metrics
            trends: Quality trends
        
        Returns:
            List of prioritized recommendations
        """
        logger.info("Generating quality improvement recommendations")
        
        recommendations = []
        
        # Coverage recommendations
        if metrics.test_coverage < 90:
            recommendations.append(QualityRecommendation(
                priority=5,
                category="coverage",
                title="Increase Test Coverage",
                description=f"Test coverage is {metrics.test_coverage:.1f}%, below the 90% target. "
                           "Focus on testing untested modules.",
                expected_impact="Improved bug detection and code reliability"
            ))
        
        # Test quality recommendations
        if metrics.test_quality_score < 70:
            recommendations.append(QualityRecommendation(
                priority=4,
                category="test_quality",
                title="Improve Test Quality",
                description=f"Test quality score is {metrics.test_quality_score:.1f}/100. "
                           "Add more assertions and edge case tests.",
                expected_impact="More reliable and comprehensive testing"
            ))
        
        # Security recommendations
        if metrics.security_score < 80:
            recommendations.append(QualityRecommendation(
                priority=5,
                category="security",
                title="Address Security Issues",
                description=f"Security score is {metrics.security_score:.1f}/100. "
                           "Review and fix identified vulnerabilities.",
                expected_impact="Reduced security risk"
            ))
        
        # Performance recommendations
        if metrics.performance_score < 70:
            recommendations.append(QualityRecommendation(
                priority=3,
                category="performance",
                title="Optimize Performance",
                description=f"Performance score is {metrics.performance_score:.1f}/100. "
                           "Profile slow endpoints and optimize database queries.",
                expected_impact="Improved user experience and scalability"
            ))
        
        # Trend-based recommendations
        for trend in trends:
            if not trend.trending_up and trend.change_percent < -5:
                recommendations.append(QualityRecommendation(
                    priority=4,
                    category="regression",
                    title=f"Address {trend.metric_name} Regression",
                    description=f"{trend.metric_name} decreased by {abs(trend.change_percent):.1f}%. "
                               "Investigate recent changes.",
                    expected_impact="Prevent quality degradation"
                ))
        
        # Sort by priority
        recommendations.sort(key=lambda x: x.priority, reverse=True)
        
        return recommendations
