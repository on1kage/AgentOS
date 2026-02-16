from agentos.task_registry import register_task_handler
from .research import execute as research_execute

register_task_handler("research", research_execute)
from .analysis import execute as analysis_execute
from agentos.task_registry import register_task_handler
register_task_handler("analysis", analysis_execute)
from .statistics import execute as statistics_execute
from agentos.task_registry import register_task_handler
register_task_handler("statistics", statistics_execute)
