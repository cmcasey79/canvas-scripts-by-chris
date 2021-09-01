################################################################################
################################################################################
## Canvas LTI paramater updater                                               ##
## Version 2021.09.01.00121                                                   ##
##                                                                            ##
## Fill in the three variables directly below this header, then run with py   ##
## **Use at your own risk.  Please try changes in Test/Beta before Prod.**    ##
##                                                                            ##
## 2021 Christopher M Casey (cmcasey79@hotmail.com)                           ##
################################################################################
################################################################################

# Canvas API token setup
# set this variabke as a valid admin API token (ex: '0001~ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789AB'
canvas_api_token=''

# Canvas subdomain setup
# set this variable as your subdomain of instructure.com (ex: 'umich')
canvas_subdomain=''

# Canvas vanity domain setup
# set this variable as your vanity domain if you have one, otherwise, leave it as '' (example: 'canvas.institution.edu')
canvas_vanity_domain=''

# Canvas account id setup
# set this variable as the account/subaccount id you'd like to work in (example: '134')
canvas_account_id=''

# Canvas environment setup
# set this variable as 'P', 'T', or 'B' for Production, Test, or Beta respectively
canvas_environment=''

################################################################################
################################################################################
## No changes to below code should be necessary.                              ##
################################################################################
################################################################################

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import json
import sys
import re

# Requests call with retry on server error
def requestswithretry(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None, ):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset({'DELETE', 'GET', 'HEAD', 'OPTIONS', 'PUT', 'TRACE', 'POST'})
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Paginated API call to Canvas
# returns list of dictionary objects from json
def canvas_get_allpages(url, headers, strip_arg=''):
    if not 'per_page=' in url:
        if '?' in url:
            url=url+'&per_page=100'
        else:
            url=url+'?per_page=100'
    rl=[] #list of JSON items converted to python dictionaries
    repeat=True
    while repeat:  
        r=requestswithretry().get(url,headers=headers)
        if r.status_code!=200:
            print('Error',r.status_code,'while retrieving get response from',url,'at',datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            repeat=False
        elif strip_arg=='':
            rl=rl+r.json()
        else:
            rl=rl+r.json()[strip_arg]
        if 'current' in r.links.keys():
            url=r.links['current']['url']
        if 'last' in r.links.keys():
            last_url=r.links['last']['url']
        else:
            last_url=''
        if url != last_url:
            if 'next' in r.links.keys():
                url=r.links['next']['url']
            else:
                repeat=False
        else:
            repeat=False
    return rl

def inputstring_to_value(inputstring):
    if inputstring=='':
        inputstring=None
    elif inputstring.isnumeric():
        inputstring=int(inputstring)
    elif inputstring.lower()=='false':
        inputstring=False
    elif inputstring.lower()=='true':
        inputstring=True
    return inputstring

# Prompt for Canvas environment selection
validated=False
while not validated:
    if canvas_subdomain=='':
        canvas_subdomain=input('Please enter your instructure.com subdomain (ex: umich): ')
    env_selection=False
    while (not env_selection):
        if canvas_environment=='':
            canvas_environment=input('Which Canvas environment would you like to work in: [P]roduction, [T]est, or [B]eta? ')
        env_selection=True
        if canvas_environment=='P' or canvas_environment=='p':
            if canvas_vanity_domain=='':
                canvas_vanity_domain==input('If applicable, please enter your Canvas vanity domain name, otherwise hit Enter (ex: canvas.institution.edu): ')
                if canvas_vanity_domain=='':
                    canvas_domain=canvas_subdomain+'.instructure.com'
                else:
                    canvas_domain=canvas_vanity_domain
            else:
                canvas_domain=canvas_vanity_domain
        elif canvas_environment.lower()=='t':
            canvas_domain=canvas_subdomain+'.test.instructure.com'
        elif canvas_environment.lower()=='b':
            canvas_domain=canvas_subdomain+'.beta.instructure.com'
        else:
            print('Invalid selection, please try again.')
            env_selection=False
            canvas_environment=''
    url='https://'+canvas_domain
    r = requests.get(url)
    if r.status_code==200 or r.status_code==401:
        print('Connection test to '+canvas_domain+' successful, proceeding...')
        validated=True
    else:
        print('Error '+str(r.status_code)+': connection to '+canvas_domain+' failed.')
        canvas_subdomain=''

# Prompt for API Token if not given
validated=False
while not validated:
    if canvas_api_token=='':
        canvas_api_token=str(input('Please enter your Canvas administrative API token: '))
    #Set HTTP headers for API calls
    get_headers={'Authorization' : 'Bearer ' + '%s' % canvas_api_token}
    put_headers={'Authorization' : 'Bearer ' + '%s' % canvas_api_token}
    url='https://'+canvas_domain+'/api/v1/accounts'
    r = requests.get(url,headers=get_headers)
    if r.status_code==200:
        print('API token validated, proceeding...')
        validated=True
    else:
        print('API token validation failed.')
        canvas_api_token=''
        
# Get account list from Canvas
url='https://'+canvas_domain+'/api/v1/accounts'
ro=[]
ro=canvas_get_allpages(url,get_headers)
account_dict={}
rosubs=[]
for i in range(len(ro)):
    account_dict[str(ro[i]['name'])]=str(ro[i]['id'])
    url2='https://'+canvas_domain+'/api/v1/accounts/'+str(ro[i]['id'])+'/sub_accounts?recursive=true'
    ro2=[]
    ro2=canvas_get_allpages(url2,get_headers)
    for j in range(len(ro2)):
        account_dict[str(ro2[j]['name'])]=str(ro2[j]['id'])

# Prompt for Canvas Account ID
validated=False
while not validated:
    if canvas_account_id=='':
        # Prompt for ID selection
        canvas_account_id=input('Which account id number would you like to work in: account_id or [L]ist)? ')
        if canvas_account_id=='L' or canvas_account_id=='l':
            for item in account_dict:
                print(account_dict[item]+': '+item)
            canvas_account_id=input('Which account id number would you like to work in? ')
    if canvas_account_id in account_dict.values():
        print('Account selection validated, proceeding...')
        validated=True
    else:
        print('Invalid account selection, please try again.')
        canvas_account_id=''

# Get LTI list from Canvas
url='https://'+canvas_domain+'/api/v1/accounts/'+canvas_account_id+'/external_tools'
ro=[]
ro=canvas_get_allpages(url,get_headers)
lti_dict={}
for i in range(len(ro)):
    lti_dict[str(ro[i]['id'])]=i

# Prompt for LTI selection
lti_parameters_dict={}
selection=False
while (not selection):
    for item in lti_dict:
        print(item+': '+ro[lti_dict[item]]['name'])
    canvas_lti_id=input('Which LTI would you like to modify (enter the id number)? ')
    if canvas_lti_id in lti_dict.keys():
        selection=True
        lti_parameters_dict=ro[lti_dict[canvas_lti_id]]
    else:
        print('Invalid selection, please try again.')

# Setup parameters for selected LTI
#print(rj)
lti_parameters_list=[]
for key in lti_parameters_dict.keys():
    if str(key)=='id' or str(key)=='created_at' or str(key)=='updated_at' or str(key)=='version':
        pass
    elif isinstance(lti_parameters_dict[key], dict):
        for key2 in lti_parameters_dict[key].keys():
            lti_parameters_list.append(str(key+'['+key2+']'))
    else:
        lti_parameters_list.append(str(key))

# Prompt for LTI parameter updates
selection=False
while (not selection):
    lti_parameters_list.sort()
    for index, value in enumerate(lti_parameters_list):
        keys = re.findall(r"\b\w+\b", value)
        if len(keys)==1:
            keyvalue=lti_parameters_dict[keys[0]]
        else:
            keyvalue=lti_parameters_dict[keys[0]][keys[1]]
        print(str(index+1)+':',value+'='+str(keyvalue))
    print('+: (Add a new parameter)')
    print('S: (Send parameters to Canvas, then exit)')
    print('X: (Exit without sending to Canvas)')
    #print(len(params)) #debug list length
    paramindex=input('Which parameter would you like to modify: (1-'+str(len(lti_parameters_list))+' or [+], [S], [X])? ')
    if paramindex=='X' or paramindex=='x':
        selection=True
    elif paramindex=='+':
        newkeyname=input('What is the name of the new parameter? ')
        if newkeyname not in lti_parameters_list:
            lti_parameters_list.append(newkeyname)
            newkeyvalue=inputstring_to_value(input('What is the value of '+newkeyname+'? '))
            keys = re.findall(r"\b\w+\b", newkeyname)
            if len(keys)==1:
                lti_parameters_dict[keys[0]]=newkeyvalue
            else:
                if lti_parameters_dict.get(keys[0])==None:
                    lti_parameters_dict[keys[0]]={}
                lti_parameters_dict[keys[0]][keys[1]]=newkeyvalue
        else:
            print('Error, parameter already exists')
    elif paramindex=='S' or paramindex=='s': 
        url='https://'+canvas_domain+'/api/v1/accounts/'+canvas_account_id+'/external_tools/'+canvas_lti_id
        r=requests.put(url,headers=put_headers,json=lti_parameters_dict)
        if r.status_code==200:
            print('LTI successfully updated!')
        else:
            print('Error ',r.status_code,'when attempting to update LTI.')
        selection=True
    elif paramindex.isnumeric() and int(paramindex)>=1 and int(paramindex)<=len(lti_parameters_list):
        newkeyvalue=inputstring_to_value(input('What is new the value of '+lti_parameters_list[int(paramindex)-1]+' (press enter to set to none)? '))
        keys = re.findall(r"\b\w+\b", lti_parameters_list[int(paramindex)-1])
        if len(keys)==1:
            lti_parameters_dict[keys[0]]=newkeyvalue
        else:
            lti_parameters_dict[keys[0]][keys[1]]=newkeyvalue
    else:
        print('Invalid selection, please try again.')

input('Press Enter to continue...')
