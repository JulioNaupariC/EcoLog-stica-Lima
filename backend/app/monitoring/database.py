"""SQL execution timing via engine-local hooks; statement values are never retained."""

from time import perf_counter

from sqlalchemy import Connection, Engine, event
from sqlalchemy.engine import ExceptionContext, ExecutionContext

from app.monitoring.metrics import Metrics


def instrument_engine(engine: Engine, metrics: Metrics, name: str) -> None:
    def before(
        conn: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        # SQLAlchemy compiled metadata avoids parsing or storing SQL and parameters.
        compiled = context.compiled
        operation = "OTHER"
        if compiled is not None:
            clause = compiled.statement
            for kind in ("select", "insert", "update", "delete"):
                if getattr(clause, "is_" + kind, False):
                    operation = kind.upper()
                    break
        context._ecolog_timing = (perf_counter(), operation)

    def finish(context: ExecutionContext, outcome: str) -> None:
        timing = getattr(context, "_ecolog_timing", None)
        if timing is None:
            return
        context._ecolog_timing = None
        started, operation = timing
        metrics.increment(
            "ecolog_database_operations_total", (name, operation, outcome)
        )
        metrics.observe(
            "ecolog_database_operation_duration_seconds",
            (name, operation),
            perf_counter() - started,
        )

    def after(
        conn: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        finish(context, "success")

    def failed(exception_context: ExceptionContext) -> None:
        if exception_context.execution_context is not None:
            finish(exception_context.execution_context, "error")

    event.listen(engine, "before_cursor_execute", before)
    event.listen(engine, "after_cursor_execute", after)
    event.listen(engine, "handle_error", failed)
