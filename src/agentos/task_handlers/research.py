def execute(task_input: str, output_path: str):
    # minimal placeholder logic for testing
    import json
    result = {"result": f"Executed research task with input: {task_input}"}
    with open(output_path, "w") as f:
        json.dump(result, f)
