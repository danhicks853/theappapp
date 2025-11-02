"""
RAG Pattern Formatting

Formats RAG patterns for injection into orchestrator prompts.
Creates structured, token-limited context for LLMs.

Reference: Section 1.5.1 - RAG System Architecture
"""
from typing import List, Dict, Any


def format_patterns(patterns: List[Dict[str, Any]], max_tokens: int = 2000) -> str:
    """
    Format RAG patterns for prompt injection.
    
    Creates structured context optimized for LLM consumption with:
    - Clear section headers
    - Success ranking
    - Token limits
    - Decision criteria
    
    Args:
        patterns: List of RAG pattern dicts
        max_tokens: Maximum tokens for formatted output (default 2000)
    
    Returns:
        Formatted string ready for prompt injection
    
    Example:
        patterns = [{"content": "...", "success_count": 5, ...}]
        context = format_patterns(patterns)
        # Inject into prompt: f"{system_prompt}\n\n{context}\n\n{user_message}"
    """
    if not patterns:
        return ""
    
    # Sort by success count (descending)
    sorted_patterns = sorted(
        patterns,
        key=lambda p: p.get("metadata", {}).get("success_count", 0),
        reverse=True
    )
    
    # Build formatted output
    lines = [
        "[ORCHESTRATOR CONTEXT: Historical Knowledge]",
        "",
        "The following patterns have been verified in past projects.",
        "Consider them when making decisions, but adapt to current context.",
        ""
    ]
    
    token_estimate = _estimate_tokens("\n".join(lines))
    patterns_included = 0
    
    for i, pattern in enumerate(sorted_patterns, 1):
        pattern_text = _format_single_pattern(pattern, i)
        pattern_tokens = _estimate_tokens(pattern_text)
        
        # Check token limit
        if token_estimate + pattern_tokens > max_tokens:
            if patterns_included == 0:
                # Include at least one pattern (truncated if needed)
                pattern_text = _truncate_to_tokens(pattern_text, max_tokens - token_estimate)
                lines.append(pattern_text)
                patterns_included += 1
            break
        
        lines.append(pattern_text)
        lines.append("")  # Blank line between patterns
        token_estimate += pattern_tokens + 1  # +1 for blank line
        patterns_included += 1
    
    # Add footer
    lines.append(f"[{patterns_included} of {len(sorted_patterns)} patterns shown]")
    lines.append("[END CONTEXT]")
    
    return "\n".join(lines)


def _format_single_pattern(pattern: Dict[str, Any], index: int) -> str:
    """Format a single pattern."""
    content = pattern.get("content", "")
    metadata = pattern.get("metadata", {})
    
    # Extract metadata
    success_count = metadata.get("success_count", 0)
    agent_type = metadata.get("agent_type", "unknown")
    task_type = metadata.get("task_type", "unknown")
    technology = metadata.get("technology", "unknown")
    quality_score = metadata.get("quality_score", "normal")
    
    # Determine ranking label
    if success_count >= 10:
        ranking = "Very Common"
    elif success_count >= 5:
        ranking = "Common"
    elif success_count >= 2:
        ranking = "Proven"
    else:
        ranking = "Verified"
    
    # Build pattern text
    header = f"Pattern {index} ({ranking} - {success_count} successes, Quality: {quality_score})"
    context_line = f"Context: {agent_type} | {task_type} | {technology}"
    
    # Parse content sections
    sections = _parse_content_sections(content)
    
    pattern_lines = [
        header,
        context_line,
        ""
    ]
    
    # Add problem section
    if "problem" in sections:
        pattern_lines.append(f"Problem: {sections['problem']}")
    
    # Add solution section
    if "solution" in sections:
        pattern_lines.append(f"Solution: {sections['solution']}")
    
    # Add when to try
    if "lesson" in sections:
        pattern_lines.append(f"When to try: {sections['lesson']}")
    elif success_count > 0:
        pattern_lines.append(f"When to try: Similar {task_type} tasks with {technology}")
    
    return "\n".join(pattern_lines)


def _parse_content_sections(content: str) -> Dict[str, str]:
    """Parse markdown sections from content."""
    sections = {}
    current_section = None
    current_content = []
    
    for line in content.split("\n"):
        line = line.strip()
        
        # Check for section headers
        if line.startswith("## "):
            # Save previous section
            if current_section and current_content:
                sections[current_section.lower()] = " ".join(current_content).strip()
            
            # Start new section
            current_section = line[3:].strip()
            current_content = []
        elif line and current_section:
            # Add to current section
            if not line.startswith("#") and not line.startswith("-"):
                current_content.append(line)
    
    # Save last section
    if current_section and current_content:
        sections[current_section.lower()] = " ".join(current_content).strip()
    
    return sections


def _estimate_tokens(text: str) -> int:
    """Rough token estimation (1 token ≈ 4 characters)."""
    return len(text) // 4


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Truncate text to fit within token limit."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    
    return text[:max_chars] + "\n... (truncated)"


def format_for_agent_context(
    patterns: List[Dict[str, Any]],
    agent_type: str,
    task_type: str,
    max_tokens: int = 1500
) -> str:
    """
    Format patterns specifically for an agent's context.
    
    Filters to most relevant patterns for the agent.
    
    Args:
        patterns: List of all patterns
        agent_type: Current agent type
        task_type: Current task type
        max_tokens: Maximum tokens
    
    Returns:
        Formatted context string
    """
    # Filter to relevant patterns
    relevant = [
        p for p in patterns
        if p.get("metadata", {}).get("agent_type") == agent_type
        or p.get("metadata", {}).get("task_type") == task_type
    ]
    
    # If no exact matches, use all patterns
    if not relevant:
        relevant = patterns
    
    return format_patterns(relevant, max_tokens)
