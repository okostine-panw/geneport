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
token = ""
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
    df2 = response(rql2)

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

# Rest of the script remains unchanged
