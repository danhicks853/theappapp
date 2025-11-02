"""
Performance Tester Service

Performance testing framework with AI optimization suggestions.
Integrates with locust for load testing and pytest-benchmark for micro-benchmarks.

Reference: Phase 3.3 - Quality Assurance System
"""
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric measurement."""
    metric_name: str
    value: float
    unit: str
    threshold: Optional[float] = None
    passed: bool = True


@dataclass
class PerformanceBenchmark:
    """Performance benchmark result."""
    endpoint: str
    method: str
    response_time_ms: float
    throughput_rps: float
    memory_mb: float
    db_query_count: int
    timestamp: str


@dataclass
class PerformanceReport:
    """Complete performance test report."""
    test_name: str
    benchmarks: List[PerformanceBenchmark]
    regressions: List[str]
    optimizations: List[str]
    overall_score: float  # 0-100
    duration_seconds: float


class PerformanceTester:
    """
    Service for performance testing with AI optimization.
    
    Features:
    - Response time measurement
    - Throughput testing
    - Memory profiling
    - Database query counting
    - Regression detection
    - AI-powered optimization suggestions
    
    Example:
        tester = PerformanceTester(llm_client)
        
        # Benchmark endpoint
        benchmark = await tester.benchmark_endpoint(
            url="http://localhost:8000/api/users",
            method="GET",
            requests=100
        )
        
        # Get optimization suggestions
        optimizations = await tester.suggest_optimizations(benchmark)
    """
    
    # Default thresholds
    DEFAULT_THRESHOLDS = {
        "response_time_ms": 200,  # Max 200ms
        "memory_mb": 100,  # Max 100MB
        "db_queries": 10,  # Max 10 queries per request
        "throughput_rps": 50,  # Min 50 requests/sec
    }
    
    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize performance tester.
        
        Args:
            llm_client: Optional LLM client for optimization suggestions
        """
        self.llm_client = llm_client
        self.baselines: Dict[str, PerformanceBenchmark] = {}
        logger.info("PerformanceTester initialized")
    
    async def benchmark_endpoint(
        self,
        url: str,
        method: str = "GET",
        requests: int = 100,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> PerformanceBenchmark:
        """
        Benchmark an API endpoint.
        
        Args:
            url: Endpoint URL
            method: HTTP method
            requests: Number of requests to send
            data: Optional request data
            headers: Optional headers
        
        Returns:
            PerformanceBenchmark with metrics
        """
        logger.info(f"Benchmarking {method} {url} with {requests} requests")
        
        import httpx
        
        response_times = []
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            for _ in range(requests):
                req_start = time.time()
                
                try:
                    if method == "GET":
                        await client.get(url, headers=headers)
                    elif method == "POST":
                        await client.post(url, json=data, headers=headers)
                    elif method == "PUT":
                        await client.put(url, json=data, headers=headers)
                    elif method == "DELETE":
                        await client.delete(url, headers=headers)
                    
                    req_end = time.time()
                    response_times.append((req_end - req_start) * 1000)  # Convert to ms
                
                except Exception as e:
                    logger.error(f"Request failed: {e}")
        
        total_time = time.time() - start_time
        
        # Calculate metrics
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        throughput = requests / total_time if total_time > 0 else 0
        
        benchmark = PerformanceBenchmark(
            endpoint=url,
            method=method,
            response_time_ms=avg_response_time,
            throughput_rps=throughput,
            memory_mb=0.0,  # TODO: Implement memory profiling
            db_query_count=0,  # TODO: Implement query counting
            timestamp=datetime.utcnow().isoformat()
        )
        
        logger.info(
            f"Benchmark complete: {avg_response_time:.2f}ms avg, "
            f"{throughput:.2f} req/s"
        )
        
        return benchmark
    
    async def detect_regressions(
        self,
        current: PerformanceBenchmark,
        baseline: Optional[PerformanceBenchmark] = None
    ) -> List[str]:
        """
        Detect performance regressions.
        
        Args:
            current: Current benchmark
            baseline: Baseline to compare against
        
        Returns:
            List of detected regressions
        """
        if not baseline:
            # Try to get stored baseline
            baseline = self.baselines.get(f"{current.method}:{current.endpoint}")
        
        if not baseline:
            logger.info("No baseline found, storing current as baseline")
            self.baselines[f"{current.method}:{current.endpoint}"] = current
            return []
        
        regressions = []
        
        # Check response time regression (>10% slower)
        if current.response_time_ms > baseline.response_time_ms * 1.1:
            increase = ((current.response_time_ms / baseline.response_time_ms) - 1) * 100
            regressions.append(
                f"Response time increased by {increase:.1f}%: "
                f"{baseline.response_time_ms:.2f}ms → {current.response_time_ms:.2f}ms"
            )
        
        # Check throughput regression (>10% slower)
        if current.throughput_rps < baseline.throughput_rps * 0.9:
            decrease = (1 - (current.throughput_rps / baseline.throughput_rps)) * 100
            regressions.append(
                f"Throughput decreased by {decrease:.1f}%: "
                f"{baseline.throughput_rps:.2f} → {current.throughput_rps:.2f} req/s"
            )
        
        return regressions
    
    async def suggest_optimizations(
        self,
        benchmark: PerformanceBenchmark,
        code_context: Optional[str] = None
    ) -> List[str]:
        """
        Generate AI-powered optimization suggestions.
        
        Args:
            benchmark: Benchmark results
            code_context: Optional code context
        
        Returns:
            List of optimization suggestions
        """
        logger.info(f"Generating optimization suggestions for {benchmark.endpoint}")
        
        suggestions = []
        
        # Heuristic-based suggestions
        if benchmark.response_time_ms > self.DEFAULT_THRESHOLDS["response_time_ms"]:
            suggestions.append(
                f"Response time ({benchmark.response_time_ms:.2f}ms) exceeds threshold "
                f"({self.DEFAULT_THRESHOLDS['response_time_ms']}ms). Consider:"
            )
            suggestions.append("- Add caching for frequently accessed data")
            suggestions.append("- Optimize database queries (add indexes, reduce N+1 queries)")
            suggestions.append("- Use async/await for I/O operations")
            suggestions.append("- Implement pagination for large result sets")
        
        if benchmark.db_query_count > self.DEFAULT_THRESHOLDS["db_queries"]:
            suggestions.append(
                f"Database query count ({benchmark.db_query_count}) is high. Consider:"
            )
            suggestions.append("- Use select_related() and prefetch_related() to reduce queries")
            suggestions.append("- Implement database query caching")
            suggestions.append("- Denormalize data where appropriate")
        
        if benchmark.throughput_rps < self.DEFAULT_THRESHOLDS["throughput_rps"]:
            suggestions.append(
                f"Throughput ({benchmark.throughput_rps:.2f} req/s) is low. Consider:"
            )
            suggestions.append("- Use connection pooling")
            suggestions.append("- Implement request queuing")
            suggestions.append("- Scale horizontally with load balancing")
        
        # LLM-powered suggestions
        if self.llm_client and code_context:
            llm_suggestions = await self._generate_llm_optimizations(
                benchmark, code_context
            )
            suggestions.extend(llm_suggestions)
        
        return suggestions
    
    async def _generate_llm_optimizations(
        self,
        benchmark: PerformanceBenchmark,
        code_context: str
    ) -> List[str]:
        """Generate optimizations using LLM (TODO: implement)."""
        logger.info("LLM optimization generation not yet implemented")
        return []
    
    async def run_load_test(
        self,
        url: str,
        users: int = 10,
        duration_seconds: int = 60,
        spawn_rate: int = 1
    ) -> PerformanceReport:
        """
        Run load test using locust.
        
        Args:
            url: Base URL to test
            users: Number of concurrent users
            duration_seconds: Test duration
            spawn_rate: Users to spawn per second
        
        Returns:
            PerformanceReport with results
        """
        logger.info(
            f"Running load test: {users} users, {duration_seconds}s duration"
        )
        
        # TODO: Implement actual locust integration
        # For now, return placeholder
        
        benchmark = await self.benchmark_endpoint(url, requests=users * 10)
        
        return PerformanceReport(
            test_name=f"load_test_{url}",
            benchmarks=[benchmark],
            regressions=[],
            optimizations=await self.suggest_optimizations(benchmark),
            overall_score=self._calculate_score(benchmark),
            duration_seconds=duration_seconds
        )
    
    def _calculate_score(self, benchmark: PerformanceBenchmark) -> float:
        """
        Calculate overall performance score (0-100).
        
        Higher is better.
        """
        score = 100.0
        
        # Deduct for slow response time
        if benchmark.response_time_ms > self.DEFAULT_THRESHOLDS["response_time_ms"]:
            penalty = min(30, (benchmark.response_time_ms / self.DEFAULT_THRESHOLDS["response_time_ms"] - 1) * 50)
            score -= penalty
        
        # Deduct for low throughput
        if benchmark.throughput_rps < self.DEFAULT_THRESHOLDS["throughput_rps"]:
            penalty = min(30, (1 - benchmark.throughput_rps / self.DEFAULT_THRESHOLDS["throughput_rps"]) * 50)
            score -= penalty
        
        return max(0, score)
