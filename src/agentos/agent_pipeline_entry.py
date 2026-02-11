import os
import sys
import argparse
import yaml
from agentos.task_registry import task_registry

from agentos.plan_runner_full_pipeline import run_full_pipeline

def execute_agent_pipeline(intent_text: str):
    payload = {"intent_text": intent_text}
    return run_full_pipeline(payload)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--plan", required=False)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--debug-tasks", action="store_true")
    args = parser.parse_args()

    if args.plan:
        plan_path = args.plan
        if not os.path.exists(plan_path):
            print(f"Plan file {plan_path} not found")
            sys.exit(1)
        with open(plan_path) as f:
            plan = yaml.safe_load(f)
        for task in plan.get("tasks", []):
            task_type = task["type"]
            task_input = task["input"]
            output_path = task["output"]
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            if task_type in task_registry:
                task_registry[task_type](task_input, output_path)
                if args.verbose or args.debug_tasks:
                    print(f"Executed {task_type}, wrote {output_path}")
            else:
                print(f"No handler registered for {task_type}")

if __name__ == "__main__":
    main()
