import lmql
@lmql.query
def generate_prompt(use_case, new_actions):
    '''lmql
    sample(temperature=0.9)
        "Based on these action(s): {new_actions} create a user_request which contains the information similar to: {use_case['Prompt']} \n\n [prompt_new]"
    from
        "openai/gpt-3.5-turbo"
    '''


