import ast
import csv
import os
import random

import openai
import pandas as pd
import re

from lmql import LMQLResult
from lmql_prompting.call_api import csv_use_case_path, csv_data_path, reAct_booking, csv_types_path, csv_results, \
    provided_endpoints, optional_endpoints, csv_results_lmql, csv_bookings_isolated_path, csv_bookings_path
from lmql_prompting.evaluate_reasoning import compare_reasoning


TEST_DATA_ITERATION = 50
MIN_HOURS_BOOKABLE = 1
MAX_HOURS_BOOKABLE = 8


def get_actions(result):
    """
    Extracts and returns the actions from the given lmql result.

    Parameters:
        result (dict): A dictionary containing the result.

    Returns:
        list: A list of strings representing the extracted actions.
    """
    variables = result.variables['REASONING']
    result = re.findall(r'Action:(.*?)Observation', variables, re.DOTALL)
    result = [action.strip() for action in result]
    return result


def get_reasoning(result):
    """
    Extracts and returns the reasoning provided by the lmql result.

    Parameters:
        result (dict): A dictionary containing the result.

    Returns:
        list: A list of strings representing the extracted actions.
    """
    try:
        variables = result.variables['REASONING']
        result = re.findall(r'Thought:(.*?)\n\nAction', variables, re.DOTALL)
        result = '\n'.join([f"{i + 1}. {item}" for i, item in enumerate(result)])
        return result
    except Exception as e:
        print("Something went wrong when evaluating the reasoning:", e)
        return None


def generate_new_reasoning(new_actions, variables, reasoning):
    """
    Create the new reasoning by replacing the necessary parameters

    Parameters:
        new actions (str): The actions in the current test data generation process
        variables (list): A list of variables that are in general available and which are placed as placeholder in the
        use_case description
        reasoning (str): Provided basic reasoning

    This function creates multiple examples based on the test data input for the given use case.
    """
    parameters = extract_values(new_actions)
    for action in parameters:
        for variable in variables:
            try:
                reasoning = reasoning.replace(variable, action[variable.replace("[", "").replace("]", "")])
            except Exception as e:
                print(f"{variable} not in {action}", e)
    return reasoning


def remove_unecessary_prompt(new_prompt):
    return new_prompt.replace("User_request_new:", "").replace("user_request_new:", "")


def generate_test_data(use_case, variables, constraints, index_use_case, index_test_data):
    """
    Generate test data based on the provided use case example.

    Parameters:
        use_case (dict): The use case description in a dictionary.
        variables, constraints (str): from get_variables_constraints()
        index_use_case (int): use case index for which test data is currently generated
        index_test_data (int): counter which is incremented for each created use case

    This function creates multiple examples (TEST_DATA_ITERATION) based on the test data input for the given use case
    and adds the created data to the test_data.csv
    """

    variables = [item.strip() for item in variables.split(',')]
    actions = use_case['Actions']
    reasoning = use_case['Reasoning']
    max_retries = 3

    for i in range(0, TEST_DATA_ITERATION):
        new_actions = replace_action_values(actions, constraints)
        new_reasoning = generate_new_reasoning(new_actions, variables, reasoning)
        for _ in range(max_retries):
            try:
                new_prompt = None
                break
            except Exception as e:
                print('Calling the LLM did not work. Retrying...', e)
                print("Retries left:", max_retries - _ - 1)
        new_prompt = remove_unecessary_prompt(new_prompt)
        test_data = pd.read_csv(csv_data_path, delimiter=";")
        index_test_data = test_data.shape[0]
        new_row = [index_use_case, index_test_data, new_prompt, new_actions, new_reasoning]
        test_data = test_data._append(pd.Series(new_row, index=test_data.columns), ignore_index=True)
        test_data.to_csv(csv_data_path, sep=';', index=False)
    return index_test_data


def extract_values(input_string):
    pattern1 = r'(\w+)\(employee:\s*([^,]+)(?:,\s*project:\s*([^,]+))?(?:,\s*time:\s*(\d+))?\)'
    pattern2 = r'(\w+)\(employee:\s*([^,]+)(?:,\s*project:\s*([^,]+))?,\s*time:\s*(\d+)\s*\)\.'

    matches = re.findall(pattern1, input_string)
    if not matches:
        matches = re.findall(pattern2, input_string)

    extracted_data = []
    for match in matches:
        endpoint, employee, project, time = match
        extracted_item = {'endpoint': endpoint, 'employee': employee.strip()}
        if project:
            extracted_item['project'] = project.strip()
        if time:
            extracted_item['time'] = time.strip()
        extracted_data.append(extracted_item)

    return extracted_data


def replace_action_values(input_string, constraints):
    extracted_data = extract_values(input_string)
    replacements = {}
    for action in extracted_data:
        for key, value in action.items():
            if value not in replacements.keys() and key != 'endpoint':
                if constraints[key] != 'INT':
                    replacements[value] = random.choice(constraints[key])
                else:
                    replacements[value] = str(random.randint(MIN_HOURS_BOOKABLE, MAX_HOURS_BOOKABLE))

    pattern = r'\b(' + '|'.join(re.escape(key) for key in replacements.keys()) + r')\b'
    output_string = re.sub(pattern, lambda x: replacements[x.group()], input_string)

    return output_string


def get_variables_constraints():
    """
    Generate variable and constraint strings based on data from a CSV file.

    Returns:
        tuple: A tuple containing two strings:
            1. variable_string (str): A string representing a list of variables.
            2. constraint_string (str): A string representing the constraints for the variables.
            This string contains a list as a string with all possible values for a variable.
    """
    data_dict = {}

    with open(csv_types_path, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            data_dict = row
    variable_string = ""
    constraint_string = ""
    constraint = {}
    counter = 1
    for key, value in data_dict.items():
        variable_string += f"[{key}]"
        if value == "INT":
            constraint_string += f"INT({key})"
            constraint[key] = value
        else:
            try:
                list(value)
                constraint_string += f"{key} in {value}"
                constraint[key] = ast.literal_eval(value)
            except Exception as e:
                print('You did not provide a correct list filled with values ', e)
        if counter < len(data_dict):
            variable_string += ", "
            constraint_string += " and "
            counter += 1
    return variable_string, constraint


def generate_test_data_from_use_case(use_case_nr=0):
    """
    Go through all provided use cases and start the process of generating test data.

    This function reads the use cases from the csv file and generates test data for each use case.

    Parameters:
    use_case_nr (int, optional): The index from where on test data should be generated.
    """
    use_cases = pd.read_csv(csv_use_case_path, sep=';')

    variables, constraints = get_variables_constraints()

    counter = 0

    for index, example in use_cases.iterrows():
        if index >= use_case_nr:
            example = example.to_dict()
            counter = generate_test_data(example, variables, constraints, index, counter)


def move_entries(source_file, dest_file):
    """
    Move entries from a source CSV file to a destination CSV file.

    Parameters:
        source_file (str): Path to the source CSV file.
        dest_file (str): Path to the destination CSV file.
    """
    # Read entries from source CSV and move them to destination CSV
    source_df = pd.read_csv(source_file, delimiter=';')
    entries_to_move = source_df.iloc[0:].copy()  # Exclude the header

    # Delete entries from source CSV
    source_df.drop(source_df.index[0:], inplace=True)
    source_df.to_csv(source_file, sep=';', index=False)

    # Append entries to destination CSV
    entries_to_move.to_csv(dest_file, mode='a', header=False, sep=';', index=False)


def go_through_test_data(use_stored_data, compare_reasoning, use_case_id):
    """
        Go through all test data that has been provided, write the prompts and compare the
        data with the generated test data and then directly post to csv file
    """
    variables, constraints = get_variables_constraints()
    split_elements = variables.split(', ')
    variables = [element.strip('[] ') for element in split_elements]
    variables_capitalized = [element.capitalize() for element in variables]
    result_actions = pd.DataFrame(
        columns=['Use_case_id', 'Test_data_id', 'Correct', 'Correct_Wrong_Order', 'Optional', 'Action_solution', 'Endpoint'] +
                variables_capitalized + ['Reasoning_correct', 'Reasoning'])
    test_data = pd.read_csv(csv_data_path, sep=';')
    counter = 0
    max_retries = 3
    results_pd = pd.read_csv(csv_results_lmql)

    for index, data in test_data.iterrows():
        if not use_stored_data and data['Use_case_id'] >= use_case_id:
            counter += 1
            for _ in range(max_retries):
                try:
                    result = reAct_booking(data['Prompt'], "")[0]
                    move_entries(csv_bookings_isolated_path, csv_bookings_path)
                    print(f"Did nr: {counter}")
                    save_to_csv(csv_results_lmql, result)
                    counter = evaluate_actions_and_reasoning(result, data['Actions'], result_actions, index,
                                                             data['Use_case_id'], counter, data['Reasoning'],
                                                             compare_reasoning,
                                                             variables)
                    break
                except Exception as e:
                    print('Calling the LLM did not work. Retrying...', e)
                    print("Retries left:", max_retries - _ - 1)
        elif use_stored_data and data['Use_case_id'] >= use_case_id:
            result = load_from_csv(results_pd, index)
            counter = evaluate_actions_and_reasoning(result, data['Actions'], result_actions, index,
                                                     data['Use_case_id'], counter, data['Reasoning'], compare_reasoning,
                                                     variables)


def save_to_csv(filename, instance):
    try:
        existing_df = pd.read_csv(filename, delimiter=";")
    except:
        existing_df = pd.DataFrame(columns=["prompt", "variables"])

    existing_df.loc[len(existing_df.index)] = [instance.prompt, instance.variables.get('REASONING')]
    existing_df.to_csv(filename, index=False, sep=";")


def load_from_csv(df, index):
    prompt = df.iloc[index]['prompt']
    variables = ast.literal_eval(df.iloc[index]['variables'])
    return [LMQLResult(prompt, variables)]


def data_formatting(result, provided_actions):
    actions = get_actions(result)
    reasoning = get_reasoning(result)
    try:
        actions = list(actions)
    except Exception as e:
        return print('Could not cast the provided actions to a list', e)

    data_result = []

    for action in actions:
        action = re.sub(r'[\'"{}]', '', action)
        action = re.sub(r'  ', '', action)
        data_result.append(extract_values(action))

    # remove all empty actions where nothing happend
    data_result = [sublist for sublist in data_result if sublist]

    data_solution = []
    provided_actions = re.sub(r'"', "'", provided_actions)
    provided_actions = ast.literal_eval(provided_actions)
    for action in provided_actions:
        action = re.sub(r'[\'"{}]', '', action)
        data_solution.append(extract_values(action))

    return data_solution, data_result, reasoning


def do_compare_reasoning(reasoning_solution, reasoning_result):
    result = compare_reasoning(reasoning_solution, reasoning_result)
    try:
        val = result[0].variables['answer']
        if val == 'true':
            return True
        else:
            return False
    except Exception as e:
        print("Something went wrong with the evaluation", e)
        return False


def initialize_status(variables):
    status = {
        'endpoint': True,
        'correct': True,
        'correct_wrong_order': False,
        'optional': False
    }
    for element in variables:
        status[element] = True
    return status


def evaluate_actions_and_reasoning(result, provided_actions, result_actions, test_data_id, use_case_id, counter,
                                   reasoning_solution, compare_reasoning, variables):
    action_solutions, action_result, reasoning_result = data_formatting(result, provided_actions)
    keys_to_compare = ['endpoint']
    [keys_to_compare.append(element) for element in variables]

    for index, action_result in enumerate(action_result):
        reasoning_correct = False
        status = initialize_status(variables)
        try:
            new_data_solution = action_solutions
            if len(action_solutions) > 0:

                # Is everything as expected?
                if action_result == action_solutions[0]:
                    new_data_solution = action_solutions[1:]
                    # If everything is as expected is also the reasoning correct?
                    if compare_reasoning:
                        reasoning_correct = do_compare_reasoning(reasoning_solution, reasoning_result)

                # Something is definitely wrong
                else:
                    status['correct'] = False
                    for key in keys_to_compare:
                        try:
                            if action_result[0][key] != action_solutions[0][0][key]:
                                # Set the corresponding variable to False
                                status[key] = False
                        except:
                            None

            if action_result not in action_solutions:
                # Something is definitely wrong
                status['correct'] = False

                # but maybe we did something optional?
                if action_result[0]['endpoint'] in optional_endpoints:
                    status['optional'] = True
                    # the reads could still be incorrect
            else:
                status['correct_wrong_order'] = True

            action_solutions = new_data_solution
        except Exception as e:
            print('Something went wrong when evaluation all inputs:', e)

        result_to_store = [use_case_id, test_data_id, status['correct'], status['correct_wrong_order'], status['optional'],
                           action_result[0], status['endpoint']]

        for element in variables:
            result_to_store.append(status[element])
        result_to_store.append(reasoning_correct)
        result_to_store.append(reasoning_result)

        result_actions.loc[counter] = result_to_store
        counter += 1

    # we have crucial actions missing:
    for action_solution in action_solutions:
        result_to_store = [use_case_id, test_data_id, False, False, False, action_solution, False]
        for el in variables:
            result_to_store.append(False)
        result_to_store.append(False)
        result_to_store.append("")
        result_actions.loc[counter] = result_to_store
        counter += 1

    result_actions.to_csv(csv_results, index=False, sep=";")
    return counter


def display_results():
    # Load the CSV file into a DataFrame
    results = pd.read_csv(csv_results, delimiter=';')

    # Filter out rows where 'Optional' is False
    results = results[results['Optional'] == False]

    # Calculate the value counts for 'Correct' column
    value_counts = results['Correct'].value_counts(normalize=True)

    # Calculate the percentage of 'Correct' values that are True
    percent_total = round(value_counts.get(True, 0) * 100, 2)

    # Group by 'Use_case_id'
    results_by_use_case_id = results.groupby('Use_case_id')

    percent_by_use_case = round(results_by_use_case_id['Correct'].mean() * 100, 2)
    percent_by_use_case_reasoning = round(results_by_use_case_id['Reasoning_correct'].mean() * 100, 2)

    # Group by both 'Use_case_id' and 'Test_data_id'
    results_grouped = results.groupby(['Use_case_id', 'Test_data_id'])
    percent_by_test_data = round(results_grouped['Correct'].mean() * 100, 2)
    percent_by_test_data_reasoning = round(results_grouped['Reasoning_correct'].mean() * 100, 2)
    percent_wrong_order = round(results_grouped['Correct_Wrong_Order'].mean() * 100, 2)

    print(f"\nPercentage total: {percent_total}% \n")
    print(f"Percentage by use_case: \n {percent_by_use_case}, {percent_by_use_case_reasoning} \n")
    print(f"Percentage by test data: \n {percent_by_test_data}, {percent_by_test_data_reasoning}, {percent_wrong_order}\n")

    unique_use_case_ids = results['Use_case_id'].unique()

    for use_case_id in unique_use_case_ids:
        use_case_data = percent_by_test_data[percent_by_test_data.index.get_level_values('Use_case_id') == use_case_id]
        percent_100 = (use_case_data == 100.00).mean() * 100
        percent_0 = (use_case_data == 0.00).mean() * 100
        print(f"Use_case {use_case_id}:")
        print(f"Percentage of 100.00 test values: {percent_100:.2f}%")
        print(f"Percentage of 0.00 test values: {percent_0:.2f}%")


def test_application():
    """
        Main function for testing the application.
        The function will go through all created use cases and for each use case,
        based on the number iteration create test data.
    """
    # generate_test_data_from_use_case(use_case_nr=0)

    # go_through_test_data(use_stored_data=False, compare_reasoning=False, use_case_id=0)

    display_results()


if __name__ == '__main__':
    test_application()
