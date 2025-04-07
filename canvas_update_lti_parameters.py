################################################################################
################################################################################
## Canvas LTI Paramater Updater                                               ##
##                                                                            ##
## Fill in the three variables directly below this header, then run with py   ##
## **Use at your own risk.  Please try changes in Test/Beta before Prod.**    ##
##                                                                            ##
## 2023 Christopher M Casey (cmcasey79@hotmail.com)                           ##
################################################################################
################################################################################

# Script mode setup
# set as '' for deault operation, 'verbose' for more detailed screen progress output or 'silent' to run without screen output.
mode=''

# Canvas API token setup
# set this variabke as a valid admin API token (ex: '0001~ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789AB'
canvas_api_token=''

# Canvas subdomain setup
# set this variable as your subdomain of instructure.com (ex: 'umich')
canvas_subdomain=''

# Canvas vanity domain setup
# set these variable as your relevant vanity domain(s) if you have them, otherwise, leave it as '' (example: 'canvas.institution.edu')
canvas_production_vanity_domain=''
canvas_beta_vanity_domain=''
canvas_test_vanity_domain=''

# Canvas account id setup
# set this variable as the account/subaccount id you'd like to work in (example: '134')
canvas_account_id=''

# Canvas environment setup
# set this variable as production, test, beta
canvas_environment=''

################################################################################
################################################################################
## No changes to below code should be necessary.                              ##
################################################################################
################################################################################
script_version='Canvas LTI Paramater Updater 2023.05.15.00123'

import socket
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from datetime import datetime, timedelta
import json
import sys
import re

scriptlog=''

#Requests call with retry on server error
def requestswithretry(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None, ):
    global scriptlog
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
# Returns a list of all items from all pages of a paginated API call
# Last updated 2015-05-16
def canvas_get_allpages(url, headers):
    global scriptlog
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
            print(datetime.now().isoformat()+': Error '+str(r.status_code)+'while retrieving get response from '+url)
            rl=None
            repeat=False
        else:
            rj=r.json()
            # if Canvas returned a single item dictionary instead of a list, try using the value of that dictionary as the list
            if type(rj) is dict:
                if len(rj.keys())==1:
                    rj=next(iter(rj.values()))
            # if a list was returned, add it to the existing list
            if type(rj) is list:
                rl=rl+rj
            url=r.links.get('current',{}).get('url',url)
            last_url=r.links.get('last',{}).get('url','')
            # if not on the last page of results, set up retrieval of next page
            if (url != last_url) and ('next' in r.links.keys()):
                url=r.links['next']['url']
            else:
                repeat=False
    return rl

# Prompt and/or validate canvas envornment information.  canvas_information is a dict which will be populated by the function.
# Prompts and/or validates the working environment, domains, api token, account_id.
# Only validates the working environment by default, but an enviromnet list in the form of ['production','beta','test'] can be passed if validation of additional environments is needed.
# Returns true if everything was properly validated, false if some information could not be valitated (signaling the script should end)
# Last updated 2023-05-15.
def canvas_validate_environment(canvas_environment, validate_environments=None):
    global scriptlog
    # Validate Canvas environment selection and domains
    domain_validated=False
    while not domain_validated:
        # Prompt for Canvas environment selection
        env_selection=False
        while (not env_selection):
            if mode[-10:]=='unattended' or canvas_environment['working_environment']!='':
                env=canvas_environment['working_environment'][0]
            else:
                env=input('Which Canvas environment would you like to work in: [P]roduction, [T]est, or [B]eta? ')
            env_selection=True
            if env.lower()=='p':
                canvas_environment['working_environment']='production'
            elif env.lower()=='t':
                canvas_environment['working_environment']='test'
            elif env.lower()=='b':
                canvas_environment['working_environment']='beta'
            else:
                if mode[-10:]=='unattended':
                    print('Invalid canvas_environment selection')
                else:
                    print('Invalid selection, please try again.')
                    env_selection=False
                canvas_environment['working_environment']=''
        if validate_environments==None:
            validate_environments=[canvas_environment['working_environment']]
        if canvas_environment['subdomain']=='' and mode[-10:]!='unattended':
            canvas_environment['subdomain']=input('Please enter your instructure.com subdomain (ex: umich): ')
        for environment in validate_environments:
            if canvas_environment['domains'][environment]=='':
                if mode[-10:]!='unattended':
                    canvas_environment['domains'][environment]=input('Please enter your '+environment+' Canvas vanity domain (hit enter if you do not have one): ')
                if canvas_environment['domains'][environment]=='':
                    canvas_environment['domains'][environment]=canvas_environment['subdomain']+('.'+environment if (environment!='' and environment!='production') else '')+'.instructure.com'
        domain_validated=True
        for environment in validate_environments:
            environment_validated=False
            url='https://'+canvas_environment['domains'][environment]
            if mode[0:6]!='silent': print(url)
            try:
                r = requests.get(url)
            except requests.exceptions.RequestException as e:
                print(datetime.now().isoformat()+': Connection error '+str(e))
                scriptlog+=datetime.now().isoformat()+': Connection error '+str(e)+'\n'
            else:
                if r.status_code==200:
                    if mode[0:6]!='silent': print(datetime.now().isoformat()+': Connection test to '+canvas_environment['domains'][environment]+' successful, proceeding...')
                    scriptlog+=datetime.now().isoformat()+': Connection test to '+canvas_environment['domains'][environment]+' successful, proceeding...\n'
                    environment_validated=True
                elif r.status_code==401:       
                    if mode[0:6]!='silent': print(datetime.now().isoformat()+': Connection test to '+canvas_environment['domains'][environment]+' successful but not validated, vanity domain or authentication may be needed, proceeding...')
                    scriptlog+=datetime.now().isoformat()+': Connection test to '+canvas_environment['domains'][environment]+' successful but not validated, vanity domain or authentication may be needed, proceeding...\n'
                    environment_validated=True
                else:
                    print(datetime.now().isoformat()+': Error '+str(r.status_code)+' - connection to '+canvas_environment['domains'][environment]+' failed.')
                    scriptlog+=datetime.now().isoformat()+': Error '+str(r.status_code)+' - connection to '+canvas_environment['domains'][environment]+' failed.\n'
            if not environment_validated:
                if canvas_environment['domains'][environment].split('.')[0]==canvas_environment['subdomain']:
                    canvas_environment['subdomain']=''
                canvas_environment['domains'][environment]=''
            domain_validated=domain_validated and environment_validated
        domain_validated=domain_validated or mode[-10:]=='unattended'
    # Validate API Token
    apitoken_validated=False
    while (not apitoken_validated) and (canvas_environment['domains'][environment]!=''):
        # Prompt for API Token if not given
        if canvas_environment['api_token']=='' and mode[-10:]!='unattended':
            canvas_environment['api_token']=str(input('Please enter your Canvas administrative API token: '))
        #Set HTTP headers for API calls
        get_headers={'Authorization' : 'Bearer '+canvas_environment['api_token']}
        put_headers={'Authorization' : 'Bearer '+canvas_environment['api_token']}
        url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/accounts'
        r = requests.get(url,headers=get_headers)
        if r.status_code==200:
            canvas_account=r.json()
            if mode[0:6]!='silent': print(datetime.now().isoformat()+': API token validated, proceeding...')
            scriptlog+=datetime.now().isoformat()+': API token validated, proceeding...\n'
            apitoken_validated=True
            canvas_environment['account_ids']['root']=canvas_account[0]['id'] if canvas_account[0]['root_account_id']==None else canvas_account[0]['root_account_id']
        else:
            print(datetime.now().isoformat()+': API token validation failed.  Token or domain settings are incorrect.')
            scriptlog+=datetime.now().isoformat()+': API token validation failed.  Token or domain settings are incorrect.\n'
            canvas_environment['api_token']=''
            if mode[-10:]=='unattended':
                apitoken_validated=True
    # Prompt for Canvas Account ID
    # Get account list from Canvas
    account_id_validated=False
    canvas_accounts_dict={}
    if canvas_environment['domains'][canvas_environment['working_environment']]!='':
        all_accounts_ids_validated=True
        for account in canvas_environment['account_ids'].keys():
            account_id_validated=False
            while (not account_id_validated and all_accounts_ids_validated):
                if account=='root':
                    account_id_validated=True
                else:
                    if canvas_environment['account_ids'][account]=='' and mode[-10:]=='unattended':
                        canvas_environment['account_ids'][account]=canvas_environment['account_ids']['root']
                        account_id_validated=True
                    else:
                        if canvas_accounts_dict=={}:
                            # Get account list from Canvas if not populated yet
                            url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/accounts'
                            canvas_accounts_list=[]
                            canvas_accounts_list=canvas_get_allpages(url,get_headers)
                            for canvas_account in canvas_accounts_list:
                                canvas_accounts_dict[canvas_account['name']]=str(canvas_account['id'])
                                url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/accounts/'+str(canvas_account['id'])+'/sub_accounts?recursive=true'
                                canvas_subaccounts_list=[]
                                canvas_subaccounts_list=canvas_get_allpages(url,get_headers)
                                for canvas_subaccount in canvas_subaccounts_list:
                                    canvas_accounts_dict[canvas_subaccount['name']]=str(canvas_subaccount['id'])
                        # Prompt for ID selection
                        if canvas_environment['account_ids'][account]=='' and mode[-10:]!='unattended':
                            canvas_environment['account_ids'][account]=input('What is the id number for the '+account+' account: # or [L]ist)? ')
                        if canvas_environment['account_ids'][account]=='L' or canvas_environment['account_ids'][account]=='l':
                            for item in canvas_accounts_dict:
                                print(canvas_accounts_dict[item]+': '+item)
                            canvas_environment['account_ids'][account]=input('What is the id number for the '+account+' account? ')
                        if str(canvas_environment['account_ids'][account]) in canvas_accounts_dict.values():
                            if mode[0:6]!='silent': print(datetime.now().isoformat()+': '+account+' account selection validated, proceeding...')
                            canvas_environment['account_ids'][account]=int(canvas_environment['account_ids'][account])
                            account_id_validated=True
                        else:
                            print(datetime.now().isoformat()+': invalid '+account+' account selection, please try again.')
                            canvas_environment['account_ids'][account]=''
                            if mode[-10:]=='unattended':
                                account_id_validated=True
            if canvas_environment['account_ids'][account]=='':
                all_accounts_ids_validated=False
    url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/users/self'
    r=requestswithretry().get(url,headers=get_headers)
    if r.status_code==200:
        canvas_user=r.json()
        if mode[0:6]!='silent': print('Running script as '+canvas_user['name']+'\n  login_id: '+canvas_user['login_id']+'\n  sis_user_id: '+canvas_user['sis_user_id']+'\n  email: '+canvas_user['email'])
        scriptlog+='Running script as '+canvas_user['name']+'\n  login_id: '+canvas_user['login_id']+'\n  sis_user_id: '+canvas_user['sis_user_id']+'\n  email: '+canvas_user['email']
    else:
        print(datetime.now().isoformat()+': Could not retrieve script user infomration.')
        scriptlog+=datetime.now().isoformat()+': Could not retrieve script user infomration..\n'
    return (canvas_environment['working_environment']!='') and (canvas_environment['domains'][canvas_environment['working_environment']]!='') and (canvas_environment['subdomain']!='') and (canvas_environment['api_token']!='') and all_accounts_ids_validated and domain_validated;

def inputstring_to_value(inputstring):
    if inputstring=='' or inputstring.lower()=='null':
        inputstring=None
    elif inputstring.isnumeric():
        inputstring=int(inputstring)
    elif inputstring.lower()=='false':
        inputstring=False
    elif inputstring.lower()=='true':
        inputstring=True
    return inputstring

hostname=socket.gethostname()
IPAddr=socket.gethostbyname(hostname)
print('Running script '+script_version+' on '+hostname+', '+IPAddr)
scriptlog+='Running script '+script_version+' on '+hostname+', '+IPAddr+'\n'

canvas_environment = {'api_token':canvas_api_token, 'subdomain':canvas_subdomain, 'working_environment':canvas_environment, 'domains':{'production':canvas_production_vanity_domain, 'test':canvas_test_vanity_domain, 'beta':canvas_beta_vanity_domain}, 'account_ids':{'root':'', 'working':canvas_account_id}}
if (not canvas_validate_environment(canvas_environment)):
    print('Canvas environment validation failed.  Exiting Script.')
else:
    get_headers={'Authorization' : 'Bearer '+canvas_environment['api_token']}
    put_headers={'Authorization' : 'Bearer '+canvas_environment['api_token']}
    delete_headers={'Authorization' : 'Bearer '+canvas_environment['api_token']}
        
    # Get LTI list from Canvas
    url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/accounts/'+str(canvas_environment['account_ids']['working'])+'/external_tools'
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

    # Prompt for LTI parameter updates
    selection=False
    while (not selection):
        lti_parameters_list=[]
        for key in lti_parameters_dict.keys():
            if str(key)=='id' or str(key)=='created_at' or str(key)=='updated_at' or str(key)=='version':
                pass
            elif isinstance(lti_parameters_dict[key], dict):
                for key2 in lti_parameters_dict[key].keys():
                    lti_parameters_list.append(str(key+'['+key2+']'))
            else:
                lti_parameters_list.append(str(key))
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
            url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/accounts/'+str(canvas_environment['account_ids']['working'])+'/external_tools/'+canvas_lti_id
            r=requests.put(url,headers=put_headers,json=lti_parameters_dict)
            if r.status_code==200:
                print('LTI successfully updated!')
                print(lti_parameters_dict)
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
