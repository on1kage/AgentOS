from agentos.agent_pipeline_entry import execute_agent_pipeline
import json

nl_input = "Describe the onemind stack components"
res = execute_agent_pipeline(nl_input)
print(json.dumps(res.__dict__, indent=2))
