# Import necessary libraries
import os
import requests
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import yaml
from collections import OrderedDict

# Configure Pandas to display entire text columns
pd.set_option('display.max_colwidth', None)

# Constants
PRISMA_API_URL = "https://api2.prismacloud.io/search/config"  # Prisma Cloud API URL
ACC_GROUPS_FILE = './accgroups.txt'  # File containing a list of account groups
STANDARDS_FILE = './templates/stds1.yaml'  # YAML file containing compliance standards
TEMPLATE_FILE = 'report.j2'  # Jinja2 template file for generating reports

# Define the URL for the Prisma Cloud API and retrieve the authentication token from environment variables
url = PRISMA_API_URL
# token = os.getenv("prisma_token")
token = "YOUR_API_TOKEN"  # Replace with your actual token

# Define headers for HTTP requests to the Prisma Cloud API
headers = {
    'Content-Type': 'application/json; charset=UTF-8',
    'Accept': 'application/json; charset=UTF-8',
    'x-redlock-auth': token
}


# Define a function to send an API request to Prisma Cloud and retrieve JSON data
def response(payload):
    """
    Send an API request to Prisma Cloud and retrieve JSON data.

    :param payload: JSON payload for the API request
    :return: A Pandas DataFrame containing the JSON response data
    """
    response = requests.request("POST", url, headers=headers, data=payload).json()['data']['items']
    return pd.json_normalize([item['data'] for item in response])


# Define a function to process results based on pass/fail criteria
def result(accgr, **params):
    """
    Process compliance check results based on pass/fail criteria.

    :param accgr: Account group identifier
    :param params: Parameters for the compliance check
    :return: A formatted result string including pass/fail information and asset details
    """
    rql1 = params['rql1'] % accgr
    rql2 = params.get('rql2', '')  # Check if 'rql2' is present, use an empty string if not

    df1 = response(rql1)

    # Check if 'rql2' is not an empty string before making the second API request
    if rql2:
        df2 = response(rql2)
    else:
        df2 = pd.DataFrame()  # Create an empty DataFrame if 'rql2' is not present

    txt1 = f"Total number of assets: {len(df2)}"

    if df1.empty and not df2.empty:
        txt2 = f"Pass: {len(df2)}"
        txt3 = f"Fail: {len(df1)}"
        assetspass = f"\nPassed assets:\n{df2[params['display_on']].to_string(header=False, index=False)}"
        assetsfail = f"\nFailed assets: None\n"
        return f"{txt1}\n{txt2}\n{txt3}\n{assetspass}\n{assetsfail}\n"

    if not df1.empty and not df2.empty:
        total = df2[params['display_on']]
        failed = df1[params['display_on']]
        passed = pd.concat([total, failed]).drop_duplicates(keep=False)
        txt2 = f"Pass: {len(passed)}"
        txt3 = f"Fail: {len(failed)}"
        assetspass = f"\nPassed assets:\n{passed.to_string(header=False, index=False)}"
        assetsfail = f"\nFailed assets:\n{failed.to_string(header=False, index=False)}"
        return f"{txt1}\n{txt2}\n{txt3}\n{assetspass}\n{assetsfail}\n"

    if df1.empty and df2.empty:
        return f"{txt1}\n"


# Read a list of account groups from a file named 'accgroups.txt'
with open(ACC_GROUPS_FILE) as f:
    accgroups = f.readlines()

# Create an ordered dictionary to store the results
outdict = OrderedDict()

# Load standards from a YAML file named 'stds.yaml' using PyYAML
standards = yaml.load(open(STANDARDS_FILE), Loader=yaml.FullLoader)

# Iterate through each account group and run compliance checks
for k, accgr in enumerate(accgroups):
    outdict.update({k: {'name': accgr.strip(), 'output': []}})
    for std in standards:
        for section in standards[std]:
            section_info = standards[std][section]['info']
            cloud_type = standards[std][section]['CloudType']
            api_info = standards[std][section]['API']
            mandatory_info = standards[std][section]['Mandatory']

            section_message = f"{section_info},{cloud_type},{api_info},{mandatory_info}"

            outdict[k]['output'].append(section_message)
            outdict[k]['output'].append(result(accgr.strip(), **standards[std][section]))
            outdict[k]['output'].append('-' * 145)  # Line of 145 '*', cosmetic

# Set up Jinja2 templating engine
env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template(TEMPLATE_FILE)

# Generate reports for each account group and write them to files
for k in outdict:
    report = f"{outdict[k]['name']}.txt"
    with open(report, 'a') as f:
        f.write(template.render(outdict[k], trim_blocks=True, lstrip_blocks=True))
