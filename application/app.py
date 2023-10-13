import csv
import logging

import pandas as pd
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
path_to_csv_isolated = '../data/bookings_isolated.csv'
path_to_csv = '../data/bookings.csv'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/book_time', methods=['POST'])
def book_time():
    # Get data from request payload
    employee = request.json['employee']
    project = request.json['project']
    time = request.json['time']

    # Write data to CSV file
    with open(path_to_csv_isolated, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([employee, project, time])

    return 'Time booking recorded successfully.'

@app.route('/read_time', methods=['GET'])
def read_time():
    employee_filter = request.args.get('employee')
    project_filter = request.args.get('project')
    time_filter = request.args.get('time')
    data = []

    # Read data from CSV file
    with open(path_to_csv_isolated, 'r') as csvfile:
        reader = csv.reader(csvfile)
        # Skip the header row (if it exists)
        next(reader, None)

        for row in reader:
            employee, project, time = row
            if (not employee_filter or employee_filter == employee) and \
               (not project_filter or project_filter == project) and \
               (not time_filter or time_filter == time):
                data.append({
                    'employee': employee,
                    'project': project,
                    'time': time
                })

    return jsonify(data)

@app.route('/delete_time', methods=['DELETE'])
def delete_time():
    try:
        employee_filter = request.json['employee']
    except:
        employee_filter = None
    try:
        project_filter = request.json['project']
    except:
        project_filter = None
    try:
        time_filter = request.json['time']
    except:
        time_filter = None

    # Read CSV file into a pandas DataFrame
    df = pd.read_csv(path_to_csv)

    # Apply filters using pandas query
    combined_filter = ""
    if employee_filter:
        combined_filter += f'employee != "{employee_filter}"'
    if project_filter:
        if combined_filter:
            combined_filter += ' and '
        combined_filter += f'project != "{project_filter}"'
    if time_filter:
        if combined_filter:
            combined_filter += ' and '
        combined_filter += f'time != "{time_filter}"'

    if combined_filter:
        df = df.query(combined_filter)

    # Write filtered data back to CSV file
    df.to_csv(path_to_csv, index=False)

    return 'Time entry deleted successfully.'

@app.route('/change_time', methods=['PUT'])
def change_time():
    # Get data from request payload
    employee_to_change = request.json['employee']
    project_to_change = request.json['project']
    new_time = request.json['new_time']

    # Read data from CSV file and find the entry to change
    with open(path_to_csv_isolated, 'r') as csvfile:
        reader = csv.reader(csvfile)
        rows = list(reader)

    found = False
    with open(path_to_csv_isolated, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['employee', 'project', 'time'])

        for row in rows:
            employee, project, time = row
            if employee == employee_to_change and project == project_to_change:
                writer.writerow([employee, project, new_time])
                found = True
            else:
                writer.writerow([employee, project, time])

    if found:
        return 'Time entry updated successfully.'
    else:
        return 'No matching entry found for the given employee and project.', 404

if __name__ == '__main__':
    app.run()
