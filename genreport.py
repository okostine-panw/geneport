import os
import csv
from jinja2 import Environment, FileSystemLoader
import pandas as pd
from collections import OrderedDict
import requests
import yaml
import configparser
import json



pd.set_option('display.max_colwidth', None)

requests.packages.urllib3.disable_warnings() # Added to avoid warnings in output if proxy

def return_error (message):
    print("\nERROR: " + message)
    exit(1)

def get_parser_from_sections_file (file_name):
    file_parser = configparser.ConfigParser()
    try: # Checks if the file has the proper format
        file_parser.read(file_name)
    except (ValueError, configparser.MissingSectionHeaderError, configparser.DuplicateOptionError, configparser.DuplicateOptionError):
        return_error ("Unable to read file " + file_name)
    return file_parser

def read_value_from_sections_file (file_parser, section, option):
    value={}
    value['Exists'] = False
    if file_parser.has_option(section, option): # Checks if section and option exist in file
        value['Value'] = file_parser.get(section,option)
        if not value['Value']=='': # Checks if NOT blank (so properly updated)
            value['Exists'] = True
    return value

def read_value_from_sections_file_and_exit_if_not_found (file_name, file_parser, section, option):
    value = read_value_from_sections_file (file_parser, section, option)
    if not value['Exists']:
        return_error("Section \"" + section + "\" and option \"" + option + "\" not found in file " + file_name)
    return value['Value']

def load_api_config (iniFilePath):
    if not os.path.exists(iniFilePath):
        return_error("Config file " + iniFilePath + " does not exist")
    iniFileParser = get_parser_from_sections_file (iniFilePath)
    api_config = {}
    api_config['BaseURL'] = read_value_from_sections_file_and_exit_if_not_found (iniFilePath, iniFileParser, 'URL', 'URL')
    api_config['AccessKey'] = read_value_from_sections_file_and_exit_if_not_found (iniFilePath, iniFileParser, 'AUTHENTICATION', 'ACCESS_KEY_ID')
    api_config['SecretKey'] = read_value_from_sections_file_and_exit_if_not_found (iniFilePath, iniFileParser, 'AUTHENTICATION', 'SECRET_KEY')
    return api_config
def handle_api_response (apiResponse):
    status = apiResponse.status_code
    if (status != 200):
        return_error ("API call failed with HTTP response " + str(status))

def run_api_call_with_payload (action, url, headers_value, payload):
    apiResponse = requests.request(action, url, headers=headers_value, data=json.dumps(payload), verify=False) # verify=False to avoid CA certificate error if proxy between script and console
    handle_api_response(apiResponse)
    return apiResponse

def run_api_call_without_payload (action, url, headers_value):
    apiResponse = requests.request(action, url, headers=headers_value, verify=False) # verify=False to avoid CA certificate error if proxy between script and console
    handle_api_response(apiResponse)
    return apiResponse
def login (api_config):
    action = "POST"
    url = api_config['BaseURL'] + "/login"
    headers = {
        'Content-Type': 'application/json'
    }
    payload = {
        'username': api_config['AccessKey'],
        'password': api_config['SecretKey'],
    }
    apiResponse = run_api_call_with_payload (action, url, headers, payload)
    authentication_response = apiResponse.json()
    token = authentication_response['token']
    return token
# ----------- Load API configuration from .ini file -----------

api_config = load_api_config("API_config.ini")

# ----------- First API call for authentication -----------

token = login(api_config)
api_config['Token'] = token
url = "https://api2.prismacloud.io/search/config"
headers = {
    'Content-Type': 'application/json; charset=UTF-8',
    'Accept': 'application/json; charset=UTF-8',
    'x-redlock-auth': token
}


def response(payload):
    response = requests.request("POST", url, headers=headers, data=payload).json()['data']['items']
    return pd.json_normalize([item['data'] for item in response])


def result(accgr, **params):
    rql1 = params['rql1'] % accgr
    rql2 = params.get('rql2', None)  # Use get to handle the case where rql2 is not present
    #rql2 = params['rql2'] % accgr
    # Use get to handle the case where rql2 is not present

    #rql2 = params.get('rql2', '')  # Check if 'rql2' is present, use an empty string if not

    df1 = response(rql1)
    df2 = response(rql2)

    total = df2[params['display_on']]
    failed = df1[params['display_on']]
    passed = pd.concat([total, failed]).drop_duplicates(keep=False)
    txt1 = f"Total number of assets:  {len(total)} "

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
        txt2 = f"Not empty Pass: {len(passed)}"
        txt3 = f"Not empty Fail: {len(failed)}"
        assetspass = f"\nPassed assets:\n{passed.to_string(header=False, index=False)}"
        assetsfail = f"\nFailed assets:\n{failed.to_string(header=False, index=False)}"
        return f"{txt1}\n{txt2}\n{txt3}\n{assetspass}\n{assetsfail}\n"
    if not df1.empty and df2.empty:
        total = df2[params['display_on']]
        failed = df1[params['display_on']]
        passed = pd.concat([total, failed]).drop_duplicates(keep=False)
        txt2 = f"Not empty Pass: {len(passed)}"
        txt3 = f"Not empty Fail: {len(failed)}"
        assetspass = f"\nPassed assets:\n{passed.to_string(header=False, index=False)}"
        assetsfail = f"\nFailed assets:\n{failed.to_string(header=False, index=False)}"
        return f"{txt1}\n{txt2}\n{txt3}\n{assetspass}\n{assetsfail}\n"
    if df1.empty and df2.empty:
        return f"{txt1}\n"
def response(payload):
    try:
        response = requests.request("POST", url, headers=headers, data=payload).json()
        data_items = response.get('data', {}).get('items', [])
        if not data_items:
            print("No 'data' or 'items' found in the API response:")
            print(response)
            return pd.DataFrame()
        return pd.json_normalize([item.get('data', {}) for item in data_items])
    except Exception as e:
        print(f"An error occurred while making the API request: {str(e)}")
        return pd.DataFrame()


with open('accgroups.txt') as f:
    accgroups = f.readlines()

outdict = OrderedDict()

standards = yaml.load(open('./templates/stds2.yaml'), Loader=yaml.FullLoader)

for k, accgr in enumerate(accgroups):
    outdict.update({k: {'name': accgr.strip(), 'output': []}})
    for std in standards:
        for section in standards[std]:
            outdict[k]['output'].append(standards[std][section]['info'])
            outdict[k]['output'].append(standards[std][section]['CloudType'])
            outdict[k]['output'].append(standards[std][section]['API'])
            outdict[k]['output'].append(standards[std][section]['Mandatory'])
            outdict[k]['output'].append(result(accgr.strip(), **standards[std][section]))
            outdict[k]['output'].append('-' * 145)  # line of 145 *, cosmetic

            section_info = standards[std][section]['info']
            cloud_type = standards[std][section]['CloudType']
            api_info = standards[std][section]['API']
            mandatory_info = standards[std][section]['Mandatory']

            section_message = f"{section_info},{cloud_type},{api_info},{mandatory_info}"

            env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('report.j2')

for k in outdict:
    report = f"{outdict[k]['name']}1.txt"
    with open(report, 'a') as f:
        f.write(template.render(outdict[k], trim_blocks=True, lstrip_blocks=True))
