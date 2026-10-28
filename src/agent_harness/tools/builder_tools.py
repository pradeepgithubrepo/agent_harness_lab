"""Safe local demonstration tools for the Builder agent."""

from langchain_core.tools import tool


@tool
def read_file(path: str) -> str:
    """Read a controlled fixture path."""
    return f"Fixture contents for {path}"


@tool
def search_code(query: str) -> str:
    """Search controlled fixture code."""
    return f"Fixture search results for {query}"


@tool
def edit_file(path: str, patch: str) -> str:
    """Record a simulated focused edit."""
    return f"Simulated edit to {path}: {patch}"


@tool
def run_tests(target: str) -> str:
    """Run a simulated fixture test target."""
    return f"Simulated tests passed: {target}"


@tool
def trigger_pipeline(name: str) -> str:
    """Demonstrate a tool that Builder policy never exposes."""
    return f"Simulated pipeline trigger: {name}"


BUILDER_TOOLS = (read_file, search_code, edit_file, run_tests, trigger_pipeline)
