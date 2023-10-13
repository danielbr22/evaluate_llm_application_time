# Mock MaibornWolff Time Application with LLM support

This project is part of the Bachelor Thesis "Investigating the Use of Large Language Models for 
Company-Related Tasks on the basis of Social Computing" at the Technical University Munich. The Thesis is supervised by 
Apl. Prof. Dr. Georg Groh and supported by Dominik Rieder (MaibornWolff GmbH).
This Repository gives an example on how Large Language Models in real world applications, looking at the MaibornWolff Time booking application.

## Description

TODO 

## Getting Started

### Requirements

  ```sh
  pip3 install -r requirements.txt 
  ```

### Running

To start the application run the following command. It will start 
the flask application so that actual values can be stored in the csv files.
You can then run the main file to take a look at the test data generation or directly call prompting functions,
e.g. in lmql_prompting in call_api.py call_api_basic(). Additionally based on the LLM you want to use you will have
to specify your individual api.env.

  ```sh
  python3 application/app.py
  ```

## Help

TODO

## Authors

- Daniel Bier (daniel.bier@tum.de)


## Version History

TODO