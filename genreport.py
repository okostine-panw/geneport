import os
import csv
from jinja2 import Environment, FileSystemLoader
import pandas as pd
from collections import OrderedDict
import requests
import yaml

pd.set_option('display.max_colwidth', None)

url = "https://api0.prismacloud.io/search/config"
token = os.getenv("prisma_token")
headers = {
  'Content-Type': 'application/json; charset=UTF-8',
  'Accept': 'application/json; charset=UTF-8',
  'x-redlock-auth': token
}

def response(payload):
  response = requests.request("POST", url, headers=headers, data=payload).json()['data']['items']
  return pd.json_normalize([item['data'] for item in response] )

def result(accgr, **params):
  rql1 = params['rql1'] % accgr
  rql2 = params['rql2'] % accgr

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
    passed = pd.concat([total,failed]).drop_duplicates(keep=False)
    txt2 = f"Pass: {len(passed)}"
    txt3 = f"Fail: {len(failed)}"
    assetspass = f"\nPassed assets:\n{passed.to_string(header=False, index=False)}"
    assetsfail = f"\nFailed assets:\n{failed.to_string(header=False, index=False)}"
    return f"{txt1}\n{txt2}\n{txt3}\n{assetspass}\n{assetsfail}\n"
  
  if df1.empty and df2.empty:
    return f"{txt1}\n"

with open('accgroups.txt') as f:
    accgroups = f.readlines()

outdict = OrderedDict()

standards = yaml.load(open('./templates/stds.yaml'), Loader=yaml.FullLoader)

for k, accgr in enumerate(accgroups):
    outdict.update({k:{ 'name': accgr.strip(), 'output':[] }})
    for std in standards:
        for section in standards[std]:
            outdict[k]['output'].append(standards[std][section]['info'])
            outdict[k]['output'].append(result(accgr.strip(), **standards[std][section]))
            outdict[k]['output'].append('-'*145) # line of 145 *, cosmetic
     
env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('report.j2')

for k in outdict:
    report = f"{outdict[k]['name']}.txt"
    with open(report, 'a') as f:
        f.write(template.render(outdict[k],trim_blocks=True, lstrip_blocks=True))