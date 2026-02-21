"""
Datadog APM wrapper. Every module calls trace_step() to create a span.
View live at: https://app.datadoghq.com/apm/traces
"""
import os
from ddtrace import tracer, patch_all
from ddtrace.filters import FilterRequestsOnUrl
from config import DD_SERVICE, DD_ENV

patch_all()

os.environ["DD_SERVICE"] = DD_SERVICE
os.environ["DD_ENV"] = DD_ENV


def trace_step(step_name: str, resource: str = None):
    """Decorator factory. Use @trace_step('recon') on any async function."""
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            with tracer.trace(step_name, service=DD_SERVICE, resource=resource or fn.__name__) as span:
                span.set_tag("penagent.target", os.getenv("TARGET_URL"))
                span.set_tag("penagent.env", DD_ENV)
                try:
                    result = await fn(*args, **kwargs)
                    span.set_tag("penagent.status", "success")
                    return result
                except Exception as e:
                    span.set_tag("penagent.status", "error")
                    span.set_tag("error.msg", str(e))
                    raise
        return wrapper
    return decorator
