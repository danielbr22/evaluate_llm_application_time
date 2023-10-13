import asyncio
import os

import lmql
from data.descriptions.book_time import instruction
import requests
import re
import json
from lmql.lib.actions import reAct, calc, wiki

# Get the current working directory
current_dir = os.getcwd()

# Create relative paths
csv_data_path = "../data/test_data.csv"
csv_use_case_path = "../data/use_cases.csv"
csv_types_path = "../data/data_types.csv"
csv_bookings_isolated_path = "../data/bookings_isolated.csv"
csv_bookings_path = "../data/bookings.csv"
csv_results = "../data/results.csv"
csv_results_lmql = "../data/results_lmql.csv"
base_url = 'http://127.0.0.1:5000'
endpoint_book = '/book_time'
endpoint_read = '/read_time'
endpoint_delete = '/delete_time'
endpoint_change = '/change_time'
provided_endpoints = ['book_time', 'read_time', 'delete_time']
optional_endpoints = ['read_time']


def make_request(params=None):
    response = requests.get(base_url + '/read_time', params=params)
    if response.status_code == 200:
        data = response.json()
        print(data)
        for entry in data:
            print(f"Employee: {entry['employee']}, Project: {entry['project']}, Time: {entry['time']}")
    else:
        print(f"Request failed with status code: {response.status_code}")


@lmql.query
def reAct_booking(content, few_shot_examples):
    '''lmql
    argmax
        "{few_shot_examples}"
        "Task: {content}"
        "A: Let's think step by step\n"

        "[REASONING]\n" where reAct(REASONING, [book_time, read_time, delete_time])

        # determine final response, after reasoning finishes
        "Request successfully handled."

    from
        "openai/gpt-3.5-turbo"
    '''


async def read_time(q: str, lookup=None):
    """
    Returns values in the local database which match the parameters.

    Example: read_time('{"employee": "Max"}')
    Result: [{'employee': 'Max', 'project': 'Bachelor Thesis', 'time': '7'}]
    """
    try:
        try:
            json_q = json.loads(q)
        except:
            return "You did not provide a String that can be converted to a JSON Object"
        response = requests.get(base_url + endpoint_read, params=json_q)
        if response.status_code == 200:
            data = response.json()
        else:
            return f"The response status code of the request is: {response.status_code}"
        return str(data)
    except:
        return "No results (try differently)"


async def book_time(q: str, lookup=None):
    """
    Adds new booking entry in the local database.

    Example: book_time('{"employee": "Max", "project": "test_project","time": 5}')
    Result: "book time: 200"
    """
    try:
        try:
            json_q = json.loads(q)
        except:
            return "You did not provide a String that can be converted to a JSON Object"
        response = requests.post(base_url + endpoint_book, json=json_q)
        if response.status_code != 200:
            return f"The response status code of the request is: {response.status_code}"
        return "book time: 200"
    except:
        return "The booking did not work correctly"


async def delete_time(q: str, lookup=None):
    """
    Deletes all entries in the local database that match the given parameters.

    Example: delete_time('{"employee": "Max", "project": "test_project","time": 5}')
    Result: delete time: 200
    """
    try:
        try:
            json_q = json.loads(q)
        except:
            return "You did not provide a String that can be converted to a JSON Object"
        response = requests.delete(base_url + endpoint_delete, json=json_q)
        if response.status_code != 200:
            return f"The response status code of the request is: {response.status_code}"
        return "delete time: 200"
    except:
        return "The deletion did not work correctly"
