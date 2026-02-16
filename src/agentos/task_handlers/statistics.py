def execute(task_input: str, output_path: str):
    import json
    result = {"result": f"Executed statistics task with input: {task_input}"}
    with open(output_path, "w") as f:
        json.dump(result, f)
