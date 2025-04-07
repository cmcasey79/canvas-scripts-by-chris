################################################################################
################################################################################
## Canvas user page view retrieval                                            ##
##                                                                            ##
## Fill in the variables directly below this header, then run with py         ##
## **Use at your own risk.  Please try changes in Test/Beta before Prod.**    ##
##                                                                            ##
## 2025 Christopher M. Casey (cmcasey79@hotmail.com)                          ##
################################################################################
################################################################################
script_version='2025.04.07.00010public'

# Canvas API token setup
# Key should be omitted for versions sent to its, will be downoloaded from server later on if last three characters of script_version is 'its' and left blank here
canvas_api_token=''

# Canvas subdomain setup
# set this variable as your subdomain of instructure.com (ex: umich)
canvas_subdomain=''

# Canvas vanity domain setup
# set these variable as your relevant vanity domain(s) if you have them, otherwise, leave it as ''
canvas_production_vanity_domain=''
canvas_beta_vanity_domain=''
canvas_test_vanity_domain=''

# Canvas account id setup
# set this variable as the account_id/subaccount_id you'd like to work in.
canvas_account_id=None

# Canvas environment setup
# set this variable as production, test, beta or leave as '' to prompt if not running in unattended mode
canvas_environment=''

################################################################################
################################################################################
## No changes to below code should be necessary.                              ##
################################################################################
################################################################################

import socket
import requests
import urllib3
import json
import datetime
import csv
import collections
import re
import urllib

scriptlog=''

#Added to suppress warnings
requests.packages.urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)

#Requests call with retry on server error
def requestswithretry(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None, ):
    session = session or requests.Session()
    retry = requests.packages.urllib3.util.retry.Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=frozenset({'DELETE', 'GET', 'HEAD', 'OPTIONS', 'PUT', 'TRACE', 'POST'})
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Paginated API call to Canvas
# Returns a tuple including list of all items from all pages of a paginated API call and the http status code and reason returned from the call(s)
# Last updated 2025-04-07 to ensure querystring parameters are urlencoded, and also accept optional json (preferred) or data dictionaries to pass on first API call
def canvas_get_allpages(url, headers, data=None, json=None):
    #ensure url path and querystring parameters are encoded properly, and add page default page limit if one is not already specificed
    url_parsed=urllib.parse.urlparse(url)
    url_parsed_query=dict(urllib.parse.parse_qsl(url_parsed.query))
    if 'per_page' not in url_parsed_query:url_parsed_query['per_page']=100
    url_parsed=url_parsed._replace(query=urllib.parse.urlencode(url_parsed_query, doseq=False),path=urllib.parse.quote(url_parsed.path))
    url=urllib.parse.urlunparse(url_parsed)
    return_data=[]
    return_key=None
    repeat=True
    canvas_request=requestswithretry().get(url,headers=headers,json=json,data=data)
    while repeat:
        if canvas_request.status_code!=200:
            repeat=False
        else:
            canvas_request_responsedata=canvas_request.json()
            # if Canvas returned a single item dictionary instead of a list, try using the value of that dictionary as the list
            if type(canvas_request_responsedata) is dict:
                if len(canvas_request_responsedata)==1:
                    return_key=list(canvas_request_responsedata.keys())[0]
                    canvas_request_responsedata=next(iter(canvas_request_responsedata.values()))
                else:
                    return_data=canvas_request_responsedata
                    repeat=False
            if type(canvas_request_responsedata) is list:
                # if a list was returned, add it to the existing list
                return_data+=canvas_request_responsedata
                url=canvas_request.links.get('current',{}).get('url',url)
                last_url=canvas_request.links.get('last',{}).get('url','')
                # if not on the last page of results, set up retrieval of next page
                if (url != last_url) and ('next' in canvas_request.links):
                    url=canvas_request.links['next']['url']
                    canvas_request=requestswithretry().get(url,headers=headers)
                else:
                    repeat=False
    return_data_namedtuple = collections.namedtuple('return_data_namedtuple', ['data', 'reason', 'status_code'])
    return return_data_namedtuple(return_data if (return_key==None) else {return_key:return_data},str(url)+': '+str(canvas_request.reason),canvas_request.status_code)

# Prompt and/or validate canvas envornment information.  Canvas_environment is a dict which will be populated by the function.
# Prompts and/or validates the working environment, domains, api token, account_id.
# Only validates the working environment by default, but an enviromnet list in the form of ['production','beta','test'] can be passed if validation of additional environments is needed.
# Returns true if everything was properly validated, false if some information could not be valitated (signaling the script should end)
# Last updated 2025-04-07.
def canvas_validate_environment(canvas_environment, validate_environments=None, mode=''):
    global scriptlog
    if mode[0:6]!='silent': print('--------------------------------------------------------------------------------\n')
    if mode[-10:]=='unattended': scriptlog+='--------------------------------------------------------------------------------\n\n'
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
                    print('Invalid canvas_environment selection.')
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
                    canvas_environment['domains'][environment]=input(f'Please enter your {environment} Canvas vanity domain (hit enter/return if you do not have one): ')
                if canvas_environment['domains'][environment]=='':
                    canvas_environment['domains'][environment]=f'{canvas_environment['subdomain']}{'.'+environment if (environment!='' and environment!='production') else ''}.instructure.com'
        domain_validated=True
        for environment in validate_environments:
            environment_validated=False
            url=f'https://{canvas_environment['domains'][environment]}'
            if mode[0:6]!='silent': print(url)
            try:
                r = requests.get(url)
            except requests.exceptions.RequestException as e:
                print(f'{datetime.datetime.now().isoformat()}: Connection error {e}')
                scriptlog+=f'{datetime.datetime.now().isoformat()}: Connection error {e}\n'
            else:
                if r.status_code==200:
                    if mode[0:6]!='silent': print(f'{datetime.datetime.now().isoformat()}: Connection test to {canvas_environment['domains'][environment]} successful, proceeding...')
                    if mode[-10:]=='unattended': scriptlog+=f'{datetime.datetime.now().isoformat()}: Connection test to {canvas_environment['domains'][environment]} successful, proceeding...\n'
                    environment_validated=True
                elif r.status_code==401:       
                    if mode[0:6]!='silent': print(f'{datetime.datetime.now().isoformat()}: Connection test to {canvas_environment['domains'][environment]} successful but not validated, vanity domain or authentication may be needed, proceeding...')
                    if mode[-10:]=='unattended': scriptlog+=f'{datetime.datetime.now().isoformat()}: Connection test to {canvas_environment['domains'][environment]} successful but not validated, vanity domain or authentication may be needed, proceeding...\n'
                    environment_validated=True
                else:
                    print(f'{datetime.datetime.now().isoformat()}: Error {r.status_code} - connection to {canvas_environment['domains'][environment]} failed.')
                    if mode[-10:]=='unattended': scriptlog+=f'{datetime.datetime.now().isoformat()}: Error {r.status_code} - connection to {canvas_environment['domains'][environment]} failed.\n'
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
        url=f'https://{canvas_environment['domains'][canvas_environment['working_environment']]}/api/v1/accounts'
        canvas_accounts = canvas_get_allpages(url,headers={'Authorization' : f'Bearer {canvas_environment['api_token']}'})
        if canvas_accounts.status_code==200:
            canvas_environment['url_headers']={'Authorization' : f'Bearer {canvas_environment['api_token']}'}
            canvas_accounts_dict={}
            for canvas_account in canvas_accounts.data:
                canvas_accounts_dict[canvas_account['id']]=canvas_account
                url=f'https://{canvas_environment['domains'][canvas_environment['working_environment']]}/api/v1/accounts/{canvas_account['id']}/sub_accounts?recursive=true'
                canvas_subaccounts=canvas_get_allpages(url,canvas_environment['url_headers'])
                if canvas_subaccounts.status_code==200:
                    for canvas_subaccount in canvas_subaccounts.data:
                        canvas_accounts_dict[canvas_subaccount['id']]=canvas_subaccount
            if mode[0:6]!='silent': print(f'{datetime.datetime.now().isoformat()}: API token validated, proceeding...')
            if mode[-10:]=='unattended': scriptlog+=f'{datetime.datetime.now().isoformat()}: API token validated, proceeding...\n'
            apitoken_validated=True
        else:
            print(f'{datetime.datetime.now().isoformat()}: API token validation failed.  Token or domain settings are incorrect.')
            if mode[-10:]=='unattended': scriptlog+=f'{datetime.datetime.now().isoformat()}: API token validation failed.  Token or domain settings are incorrect.\n'
            canvas_environment['api_token']=''
            canvas_environment['url_headers']=''
            if mode[-10:]=='unattended': apitoken_validated=True
    # Prompt for Canvas Account ID
    # Get account list from Canvas
    account_id_validated=False
    if canvas_environment['domains'][canvas_environment['working_environment']]!='':
        all_accounts_ids_validated=True
        all_root_account_ids=set()
        for account in (set(canvas_environment['account_ids'].keys())-set(['root'])):
            account_id_validated=False
            while (not account_id_validated and all_accounts_ids_validated):
                if canvas_environment['account_ids'][account]=='' and mode[-10:]=='unattended':
                    canvas_environment['account_ids'][account]=canvas_environment['account_ids']['root']
                    account_id_validated=True
                else:
                    # Prompt for ID selection
                    if canvas_environment['account_ids'][account]=='' and mode[-10:]!='unattended':
                        canvas_environment['account_ids'][account]=input(f'What is the id number for the {account} account: # or [L]ist)? ')
                    if str(canvas_environment['account_ids'][account]).lower()=='l':
                        for account_id in canvas_accounts_dict:
                            print(str(account_id)+': '+canvas_accounts_dict[account_id]['name'])
                        canvas_environment['account_ids'][account]=input(f'What is the id number for the {account} account? ')
                    if (type(canvas_environment['account_ids'][account])==int or (type(canvas_environment['account_ids'][account])==str and (canvas_environment['account_ids'][account].isdigit()))) and (int(canvas_environment['account_ids'][account]) in canvas_accounts_dict):
                        canvas_environment['account_ids'][account]=int(canvas_environment['account_ids'][account])
                        if mode[0:6]!='silent': print(f'{datetime.datetime.now().isoformat()}: {account} account selection validated (account_id: {canvas_environment['account_ids'][account]}, account_name: {canvas_accounts_dict[canvas_environment['account_ids'][account]]['name']}), proceeding...')
                        if mode[-10:]=='unattended': scriptlog+=f'{datetime.datetime.now().isoformat()}: {account} account selection validated (account_id: {canvas_environment['account_ids'][account]}, account_name: {canvas_accounts_dict[canvas_environment['account_ids'][account]]['name']}), proceeding...\n'
                        account_id_validated=True
                        account_root_id=canvas_environment['account_ids'][account]
                        while canvas_accounts_dict[account_root_id]['parent_account_id']!=None:
                            account_root_id=canvas_accounts_dict[account_root_id]['parent_account_id']
                        all_root_account_ids.add(account_root_id)
                    else:
                        print(f'{datetime.datetime.now().isoformat()}: invalid {account} account selection (account_id: {canvas_environment['account_ids'][account]}).')
                        if mode[-10:]=='unattended':scriptlog+=f'{datetime.datetime.now().isoformat()}: invalid {account} account selection (account_id: {canvas_environment['account_ids'][account]}).\n'
                        canvas_environment['account_ids'][account]=''
                        if mode[-10:]=='unattended':
                            account_id_validated=True
            if canvas_environment['account_ids'][account]=='':
                all_accounts_ids_validated=False
        canvas_environment['account_ids']['root']=min(all_root_account_ids)
        if len(all_root_account_ids)==1:
            if mode[0:6]!='silent': print(f'{datetime.datetime.now().isoformat()}: root account selection validated (account_id: {canvas_environment['account_ids']['root']}, account_name: {canvas_accounts_dict[canvas_environment['account_ids']['root']]['name']}), proceeding...')
            if mode[-10:]=='unattended': scriptlog+=f'{datetime.datetime.now().isoformat()}: root account selection validated (account_id: {canvas_environment['account_ids']['root']}, account_name: {canvas_accounts_dict[canvas_environment['account_ids']['root']]['name']}), proceeding...\n'
        else:
            print('Specified accounts belong to different root accounts, unable to continue...')
            if mode[-10:]=='unattended': scriptlog+='Specified accounts belong to different root accounts, unable to continue...\n'
            all_accounts_ids_validated=False
    if canvas_environment['domains'][canvas_environment['working_environment']]!='':
        url=f'https://{canvas_environment['domains'][canvas_environment['working_environment']]}/api/v1/users/self'
        r=requestswithretry().get(url,headers=canvas_environment['url_headers'])
        if r.status_code==200:
            canvas_user=r.json()
            if mode[0:6]!='silent': print(f'Running script as {canvas_user['name']}\n  login_id: {canvas_user['login_id']}\n  sis_user_id: {canvas_user['sis_user_id']}\n  email: {canvas_user['email']}')
            if mode[-10:]=='unattended': scriptlog+=f'Running script as {canvas_user['name']}\n  login_id: {canvas_user['login_id']}\n  sis_user_id: {canvas_user['sis_user_id']}\n  email: {canvas_user['email']}\n\n'
        else:
            print(f'{datetime.datetime.now().isoformat()}: Could not retrieve script user infomration.')
            if mode[-10:]=='unattended': scriptlog+=f'{datetime.datetime.now().isoformat()}: Could not retrieve script user infomration..\n'
    if mode[0:6]!='silent': print('\n--------------------------------------------------------------------------------\n')
    if mode[-10:]=='unattended': scriptlog+='\n--------------------------------------------------------------------------------\n\n'
    return (canvas_environment['working_environment']!='') and (canvas_environment['domains'][canvas_environment['working_environment']]!='') and (canvas_environment['subdomain']!='') and (canvas_environment['api_token']!='') and all_accounts_ids_validated and domain_validated;

# Return a canvas global id given an input id, the full domain name relating to the id, and a lookup domain acount info dictionary.
# returtype is opional and works as follows
#   'int' returns integer format of shard and id, ex: 10000000000001
#   'string' returns stringified integer format of shard and id, ex: '10000000000001'
#   'shortstring' returns shard_id ~ item_id, ex: '1~1'
# Canvas API calls should accpet any of the above formats
# Last updated 2025-03-23.
def canvas_gid_from_id_domain(canvas_id,canvas_domain,canvas_domain_account_info,returntype='shortstring'):
    if canvas_domain not in canvas_domain_account_info:
        url=f'https://{canvas_domain}/api/v1/accounts'
        canvas_account_request=canvas_get_allpages(url,canvas_environment['url_headers'])
        if canvas_account_request.status_code!=200:
            print(f'Error {canvas_account_request.status_code} retrieving accounts list for {domain}')
        else:
            for canvas_account in canvas_account_request.data:
                if canvas_account['root_account_id']==None and canvas_account['id']<10000000000000:
                    canvas_domain_account_info[canvas_domain]=canvas_domain_account_info.pop(canvas_account['uuid'])
    if canvas_id!=None:
        if isinstance(canvas_id,str):
            if canvas_id.isnumeric():
                canvas_id=int(canvas_id)
            else:
                canvas_id=int(canvas_id[:canvas_id.index('~')])*10000000000000+int(canvas_id[canvas_id.index('~')+1:])
#        The following line should be the standard.  Replaced with the 3 following lines due to Canvas API returning incorrect shardid in some results, revert back to default when the issue is corrected.
#        canvas_shard_id=canvas_id//10000000000000 if canvas_id>=10000000000000 else canvas_domain_account_info.get(canvas_domain,{}).get('shard_id',0)
        canvas_shard_from_id=canvas_id//10000000000000 if canvas_id>=10000000000000 else 0
        canvas_shard_from_domain=canvas_domain_account_info.get(canvas_domain,{}).get('shard_id',0)
        canvas_shard_id=canvas_shard_from_domain if (canvas_shard_from_id==0 or canvas_shard_from_id-canvas_shard_from_domain==20000) else canvas_shard_from_id
        canvas_id=canvas_id%10000000000000
        match returntype:
            case 'shortstring':
                returndata=f'{canvas_shard_id}~{canvas_id}'
            case 'string':
                returndata=str(canvas_shard_id*10000000000000+canvas_id)
            case 'int':
                returndata=canvas_shard_id*10000000000000+canvas_id
            case _:
                returndata=None
    return returndata if canvas_id!=None else None

def main():
    global scriptlog, canvas_api_token, canvas_subdomain, canvas_environment, canvas_production_vanity_domain, canvas_test_vanity_domain, canvas_beta_vanity_domain, canvas_account_id
    hostname=socket.gethostname()
    IPAddr=socket.gethostbyname(hostname)
    print(f'Running script version {script_version} on {hostname}, {IPAddr}')
    scriptlog+=f'Running script version {script_version} on {hostname}, {IPAddr}\n'
    start_time = datetime.datetime.now()

    canvas_environment = {'api_token':str(canvas_api_token),
                          'url_headers':{'Authorization' : 'Bearer '+str(canvas_api_token)},
                          'subdomain':str(canvas_subdomain),
                          'working_environment':canvas_environment,
                          'domains':{'production':canvas_production_vanity_domain, 'test':canvas_test_vanity_domain, 'beta':canvas_beta_vanity_domain},
                          'account_ids':{'root':'', 'working':canvas_account_id}}
    if (not canvas_validate_environment(canvas_environment)):
        print('Canvas environment validation failed.  Exiting Script.')
        scriptlog+='Canvas environment validation failed.  Exiting Script.\n'
    else:
        canvas_domain_account_info={}
        for canvas_domain in filter(None,canvas_environment['domains'].values()):
            url=f'https://{canvas_domain}/api/v1/accounts'
            canvas_account_request=canvas_get_allpages(url,canvas_environment['url_headers'])
            if canvas_account_request.status_code!=200:
                print(f'Error {canvas_account_request.status_code} retrieving accounts list for {domain}')
            else:
                for canvas_account in canvas_account_request.data:
                    if canvas_account['root_account_id']==None:
                        if canvas_account['id']<10000000000000:
                            canvas_domain_account_info[canvas_domain]={'shard_id':int(canvas_environment['api_token'][:canvas_environment['api_token'].index('~')]),'root_account_id':canvas_account['id']}
                        else:
                            canvas_domain_account_info[canvas_account['uuid']]={'shard_id':canvas_account['id']//10000000000000,'root_account_id':canvas_account['id']%10000000000000}
        canvas_user_info={}
        canvas_course_info={}
        canvas_group_info={}
        canvas_account_info={}
        canvas_external_tool_info={}
        canvas_target_user_id=input('Please enter the canvas_user_id of the user which you wish to see the page view history: ')
        url=f'https://{canvas_environment['domains'][canvas_environment['working_environment']]}/api/v1/users/{canvas_target_user_id}'
        canvas_target_user_request=canvas_get_allpages(url,canvas_environment['url_headers'])
        if canvas_target_user_request.status_code!=200:
            print(f'{datetime.datetime.now().isoformat()}: Could not target canvas user infomration.')
        else:
            print(f'Retrieving pageviews for {canvas_target_user_request.data['name']}\n  login_id: {canvas_target_user_request.data['login_id']}\n  sis_user_id: {canvas_target_user_request.data['sis_user_id']}\n  email: {canvas_target_user_request.data['email']}\n')
            pageview_start_datetime_localstring=input('Enter start date, formatted yyyy-mm-dd: ')
            while pageview_start_datetime_localstring!='' and re.match(r'\d{4}-[0-1][1-9]-[0-3][1-9]',pageview_start_datetime_localstring)==None:
                pageview_start_datetime_localstring=input('Enter start date, formatted yyyy-mm-dd: ')
            pageview_start_datetime=datetime.datetime.fromisoformat(pageview_start_datetime_localstring).astimezone() if pageview_start_datetime_localstring!='' else None
            pageview_start_datetime_zulustring=pageview_start_datetime.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z") if pageview_start_datetime!=None else None
            print('Start date/time zulustring:', pageview_start_datetime_zulustring,'\n')
            pageview_end_datetime_localstring=input('Enter end date, formatted yyyy-mm-dd: ')
            while pageview_end_datetime_localstring!='' and re.match(r'\d{4}-[0-1][1-9]-[0-3][1-9]',pageview_end_datetime_localstring)==None:
                pageview_end_datetime_localstring=input('Enter end date, formatted yyyy-mm-dd: ')
            pageview_end_datetime=datetime.datetime.fromisoformat(pageview_end_datetime_localstring+'T23:59:59').astimezone() if pageview_end_datetime_localstring!='' else None
            pageview_end_datetime_zulustring=pageview_end_datetime.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")  if pageview_end_datetime!=None else None
            print('End_date/time zulustring:', pageview_end_datetime_zulustring,'\n')

            if pageview_start_datetime!=None and pageview_end_datetime!=None and pageview_start_datetime>=pageview_end_datetime:
                print('Error: start date/time must be before end date/time')
            else:
                start_time = datetime.datetime.now()
                url=f'https://{canvas_environment['domains'][canvas_environment['working_environment']]}/api/v1/users/{canvas_target_user_id}/page_views'
                data={}
                if pageview_end_datetime_zulustring!=None:
                    data['end_time']=pageview_end_datetime_zulustring
                if pageview_start_datetime_zulustring!=None:
                    data['start_time']=pageview_start_datetime_zulustring
                canvas_user_pageviews_response=canvas_get_allpages(url,canvas_environment['url_headers'],data=data)
                print('User had',len(canvas_user_pageviews_response.data),'total page views in the specified period (including admins acting as).\n')
                if canvas_target_user_request.status_code==200 and len(canvas_user_pageviews_response.data)>0:
                    canvas_user_pageviews=canvas_user_pageviews_response.data
                    for pageview in canvas_user_pageviews:
                        pageview['domain']=pageview['url'].split('/')[2]
                        pageview['user_id']=canvas_gid_from_id_domain(pageview['links']['user'],canvas_environment['domains'][canvas_environment['working_environment']],canvas_domain_account_info)
                        pageview['real_user_id']=canvas_gid_from_id_domain(pageview['links']['real_user'],canvas_environment['domains'][canvas_environment['working_environment']],canvas_domain_account_info)
                        pageview['user_sis_id']=canvas_target_user_request.data['sis_user_id']
                        pageview['user_login_id']=canvas_target_user_request.data['login_id']
                        pageview['user_name']=canvas_target_user_request.data['name']
                        pageview['account_id']=canvas_gid_from_id_domain(pageview['links']['account'],canvas_environment['domains'][canvas_environment['working_environment']],canvas_domain_account_info)
                        if pageview['account_id']!=None and pageview['account_id'] not in canvas_account_info:
                            url=f'https://{canvas_environment['domains'][canvas_environment['working_environment']]}/api/v1/accounts/{pageview['account_id']}'
                            canvas_account_info[pageview['account_id']]=canvas_get_allpages(url,canvas_environment['url_headers']).data
                        pageview['account_name']=canvas_account_info[pageview['account_id']]['name']
                        pageview['context_id']=canvas_gid_from_id_domain(pageview['links']['context'],canvas_environment['domains'][canvas_environment['working_environment']],canvas_domain_account_info)
                        pageview['asset_id']=pageview['links']['asset']
                        del pageview['links']
                        pageview['context_group_id']=canvas_gid_from_id_domain(pageview['context_id'],pageview['domain'],canvas_domain_account_info) if pageview['context_type']=='Group' else None
                        if pageview['context_group_id']!=None and pageview['context_group_id'] not in canvas_group_info:
                            url=f'https://{canvas_environment['domains'][canvas_environment['working_environment']]}/api/v1/groups/{pageview['context_group_id']}'
                            canvas_group_info[pageview['context_group_id']]=canvas_get_allpages(url,canvas_environment['url_headers']).data
                            canvas_group_info[pageview['context_group_id']]['id']=canvas_gid_from_id_domain(canvas_group_info[pageview['context_group_id']]['id'],pageview['domain'],canvas_domain_account_info)
                            canvas_group_info[pageview['context_group_id']]['course_id']=canvas_gid_from_id_domain(canvas_group_info[pageview['context_group_id']]['course_id'],pageview['domain'],canvas_domain_account_info)
                        pageview['context_group_name']=canvas_group_info.get(pageview['context_group_id'],{}).get('name')
                        pageview['context_course_id']=canvas_gid_from_id_domain(pageview['context_id'] if pageview['context_type']=='Course' else (canvas_group_info[pageview['context_group_id']]['course_id'] if pageview['context_type']=='Group' else None),pageview['domain'],canvas_domain_account_info)
                        if pageview['context_course_id']!=None and pageview['context_course_id'] not in canvas_course_info:
                            url=f'https://{canvas_environment['domains'][canvas_environment['working_environment']]}/api/v1/courses/{pageview['context_course_id']}'
                            canvas_course_info[pageview['context_course_id']]=canvas_get_allpages(url,canvas_environment['url_headers']).data
                            canvas_course_info[pageview['context_course_id']]['id']=canvas_gid_from_id_domain(canvas_course_info[pageview['context_course_id']]['id'],pageview['domain'],canvas_domain_account_info)
                            canvas_course_info[pageview['context_course_id']]['account_id']=canvas_gid_from_id_domain(canvas_course_info[pageview['context_course_id']]['account_id'],pageview['domain'],canvas_domain_account_info)
                        pageview['context_course_name']=canvas_course_info.get(pageview['context_course_id'],{}).get('name') if pageview['context_course_id']!=None else None
                        pageview['context_account_id']=pageview['context_id'] if pageview['context_type']=='Account' else (canvas_course_info[pageview['context_course_id']]['account_id'] if pageview['context_course_id']!=None else canvas_gid_from_id_domain(canvas_domain_account_info[pageview['domain']]['root_account_id'],pageview['domain'],canvas_domain_account_info))
                        if pageview['context_account_id']!=None and pageview['context_account_id'] not in canvas_account_info:
                            url=f'https://{canvas_environment['domains'][canvas_environment['working_environment']]}/api/v1/accounts/{pageview['context_account_id']}'
                            canvas_account_info[pageview['context_account_id']]=canvas_get_allpages(url,canvas_environment['url_headers']).data
                        pageview['context_account_name']=canvas_account_info.get(pageview['context_account_id'],{}).get('name')
                        pageview['context_user_id']=pageview['context_id'] if pageview['context_type']=='User' else None
                        if pageview['context_user_id']!=None and pageview['context_user_id'] not in canvas_user_info:
                            url=f'https://{canvas_environment['domains'][canvas_environment['working_environment']]}/api/v1/users/{pageview['context_user_id']}'
                            canvas_user_info[pageview['context_user_id']]=canvas_get_allpages(url,canvas_environment['url_headers']).data
                        pageview['context_user_name']=canvas_user_info.get(pageview['context_user_id'],{}).get('name')
                        pageview['context_external_tool_id']=re.search(r'external_tools/\d+',pageview['url']) if (pageview['action']=='external_tool' or pageview['controller']=='external_tools') else None
                        if pageview['context_external_tool_id']!=None:
                            pageview['context_external_tool_id']=canvas_gid_from_id_domain(int(pageview['context_external_tool_id'].group(0)[15:]),pageview['domain'],canvas_domain_account_info)
                        if pageview['context_external_tool_id']!=None and pageview['context_external_tool_id'] not in canvas_external_tool_info:
                            url=f'https://{pageview['domain']}/api/v1/courses/{pageview['context_course_id']}/external_tools/{pageview['context_external_tool_id']}'
                            canvas_external_tool_request=canvas_get_allpages(url,canvas_environment['url_headers'])
                            canvas_account_id=pageview['context_account_id']
                            while canvas_external_tool_request.status_code!=200 and canvas_account_id:
                                url=f'https://{pageview['domain']}/api/v1/accounts/{canvas_account_id}/external_tools/{pageview['context_external_tool_id']}'
                                canvas_external_tool_request=canvas_get_allpages(url,canvas_environment['url_headers'])
                                if canvas_external_tool_request.status_code!=200:
                                    url=f'https://{pageview['domain']}/api/v1/accounts/{canvas_account_id}'
                                    canvas_account_request=canvas_get_allpages(url,canvas_environment['url_headers'])
                                    canvas_account_id=canvas_gid_from_id_domain(canvas_account_request.data['parent_account_id'],pageview['domain'],canvas_domain_account_info)
                            canvas_external_tool_info[pageview['context_external_tool_id']]={} if canvas_external_tool_request.data==None else canvas_external_tool_request.data
                        pageview['external_tool_name']=canvas_external_tool_info.get(pageview['context_external_tool_id'],{}).get('name')
                    canvas_user_self_pageviews = [pageview for pageview in canvas_user_pageviews if (pageview['real_user_id']==None and pageview['app_name']!='U-M Maizey AI')]
                    print('User had',len(canvas_user_self_pageviews),'self page views in the specified period.\n')
                    with open('pageviews-all.csv', 'w', newline='') as output_file:
                        if len(canvas_user_self_pageviews)>0:
                            writer = csv.DictWriter(output_file, canvas_user_self_pageviews[0].keys())
                            writer.writeheader()
                            writer.writerows(canvas_user_self_pageviews)
                    canvas_user_self_participation_pageviews = [pageview for pageview in canvas_user_self_pageviews if pageview['participated']==True]
                    print('User had',len(canvas_user_self_participation_pageviews),'self partipation page views in the specified period.\n')
                    with open('pageviews-participations.csv', 'w', newline='') as output_file:
                        if len(canvas_user_self_pageviews)>0:
                            writer = csv.DictWriter(output_file, canvas_user_self_pageviews[0].keys())
                            writer.writeheader()
                            if len(canvas_user_self_participation_pageviews)>0:
                                writer.writerows(canvas_user_self_participation_pageviews)
                print(f'Finished!  Run time: {datetime.datetime.now() - start_time}')
                scriptlog+=(f'\nFinished!  Run time: {datetime.datetime.now() - start_time}\n')

if __name__=='__main__':
    main()
