"""
Langfuse compatibility helper to handle different versions and import issues.
"""

def noop_decorator(func):
    """No-op decorator that does nothing but return the original function."""
    return func

def noop_context_manager(*args, **kwargs):
    """No-op context manager that does nothing."""
    pass

# Try to import langfuse decorators, with fallbacks
try:
    from langfuse.decorators import observe, langfuse_context
except ImportError:
    try:
        from langfuse import observe, langfuse_context
    except ImportError:
        # Create mock implementations if langfuse is not available
        observe = noop_decorator
        
        class MockLangfuseContext:
            def update_current_trace(self, **kwargs):
                pass
        
        langfuse_context = MockLangfuseContext()

# Export the compatible imports
__all__ = ['observe', 'langfuse_context']
