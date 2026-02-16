task_registry = {}

def register_task_handler(task_type, func):
    task_registry[task_type] = func
