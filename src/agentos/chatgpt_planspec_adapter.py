def chatgpt_nl_to_planspec(nl_text: str) -> dict:

    mapping = {
        'describe the onemind stack components': {
            'intent_text': nl_text,
            'plan_spec': {
                'role': 'morpheus',
                'action': 'architecture',
                'metadata': {
                    'request': 'describe_onemind_stack_components'
                }
            }
        }
    }

    return mapping.get(nl_text.strip().lower(), {
        'intent_text': nl_text,
        'plan_spec': {}
    })
