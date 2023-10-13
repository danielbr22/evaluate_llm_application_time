import lmql

@lmql.query
def compare_reasoning(solution, result):
    '''lmql
    argmax
        "Do these two statements have the same meaning? Statement 1: {solution}\n\n Statement 2: {result}\n\n The statements have the same meaning: [answer]"
    from
        "openai/text-davinci-003"
    where answer in set(["true","false"])
    '''