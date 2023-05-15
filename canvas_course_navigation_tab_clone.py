################################################################################
################################################################################
## Canvas course navigation lti replacement tab mimicer                       ##
##                                                                            ##
## Fill in the three variables directly below this header, then run with py   ##
## **Use at your own risk.  Please try changes in Test/Beta before Prod.**    ##
##                                                                            ##
## 2022 Christopher M. Casey (cmcasey79@hotmail.com)                          ##
################################################################################
################################################################################
script_version='2022.12.20.00008'

# Script mode setup
# set as 'unattended' to run without prompts using the info below, otherwise leave as ''
mode=''

# Canvas API token setup
# set this variabke as a valid admin API token
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
# set this variable as the account/subaccount id you'd like to work in.  If left blank, script will run for root account.
canvas_account_id=''

# Canvas environment setup
# set this variable as 'production', 'test', or 'beta'
canvas_environment=''

################################################################################
################################################################################
## No changes to below code should be necessary.                              ##
################################################################################
################################################################################

#Set HTTP headers for API calls
get_headers={'Authorization' : 'Bearer ' + '%s' % canvas_api_token}
put_headers={'Authorization' : 'Bearer ' + '%s' % canvas_api_token}
scriptlog=''

import socket
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
import json
from datetime import datetime, timedelta
import csv

#Added to suppress warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

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
# returns list of dictionary objects from json
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
            print(datetime.now().isoformat()+': Error',r.status_code,'while retrieving get response from ',url)
            rl=None
            repeat=False
        else:
            rj=r.json()
            if type(rj) is dict:
                for key in rj:
                    rl=rl+rj[key]
            else:
                rl=rl+rj
            url=r.links.get('current',{}).get('url',url)
            last_url=r.links.get('last',{}).get('url','')
            if (url != last_url) and ('next' in r.links.keys()):
                url=r.links['next']['url']
            else:
                repeat=False
    return rl

# Prompt and/or validate canvas envornment information.  canvas_information is a dict which will be populated by the function.
# Prompts and/or validates the working environment, domains, api token, account_id.
# Returns true if everything was properly validated, false if some information could not be valitated (signaling the script should end)
# Last updated 2022-09-22.
def validate_canvas_environment(canvas_environment):
    global scriptlog
    # Validate Canvas environment selection and domains
    domain_validated=False
    while not domain_validated:
        # Prompt for Canvas environment selection
        if canvas_environment['subdomain']=='' and mode!='unattended':
            canvas_environment['subdomain']=input('Please enter your instructure.com subdomain (ex: umich): ')
        if canvas_environment['domains']['production']=='':
            if mode!='unattended':
                canvas_environment['domains']['production']=input('Please enter your production Canvas vanity domain (hit enter if you do not have one)')
            if canvas_environment['domains']['production']=='':
                canvas_environment['domains']['production']=canvas_environment['subdomain']+'.instructure.com'
        if canvas_environment['domains']['beta']=='':
            if mode!='unattended':
                canvas_environment['domains']['beta']=input('Please enter your beta Canvas vanity domain (hit enter if you do not have one): ')
            if canvas_environment['domains']['beta']=='':
                canvas_environment['domains']['beta']=canvas_environment['subdomain']+'.beta.instructure.com'
        if canvas_environment['domains']['test']=='':
            if mode!='unattended':
                canvas_environment['domains']['test']=input('Please enter your test Canvas vanity domain (hit enter if you do not have one): ')
            if canvas_environment['domains']['test']=='':
                canvas_environment['domains']['test']=canvas_environment['subdomain']+'.test.instructure.com'
        env_selection=False
        while (not env_selection):
            if mode=='unattended' or canvas_environment['working_environment']!='':
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
                if mode=='unattended':
                    print('Invalid canvas_environment selection')
                else:
                    print('Invalid selection, please try again.')
                    env_selection=False
                canvas_environment['working_environment']=''
        for environment in ['production','beta','test']:
            environment_validated=False
            url='https://'+canvas_environment['domains'][environment]
            print(url)
            try:
                r = requestswithretry().get(url)
            except requests.exceptions.RequestException as e:
                print(datetime.now().isoformat()+': Connection error '+str(e))
                scriptlog+=datetime.now().isoformat()+': Connection error '+str(e)+'\n'
            else:
                if r.status_code==200:
                    print(datetime.now().isoformat()+': Connection test to '+canvas_environment['domains'][environment]+' successful, proceeding...')
                    scriptlog+=datetime.now().isoformat()+': Connection test to '+canvas_environment['domains'][environment]+' successful, proceeding...\n'
                    environment_validated=True
                elif r.status_code==401:       
                    print(datetime.now().isoformat()+': Connection test to '+canvas_environment['domains'][environment]+' successful but not validated, vanity domain or authentication may be needed, proceeding...')
                    scriptlog+=datetime.now().isoformat()+': Connection test to '+canvas_environment['domains'][environment]+' successful but not validated, vanity domain or authentication may be needed, proceeding...\n'
                    environment_validated=True
                else:
                    print(datetime.now().isoformat()+': Error '+str(r.status_code)+' - connection to '+canvas_environment['domains'][environment]+' failed.')
                    scriptlog+=datetime.now().isoformat()+': Error '+str(r.status_code)+' - connection to '+canvas_environment['domains'][environment]+' failed.\n'
            if not environment_validated:
                if canvas_environment['domains'][environment].split('.')[0]==canvas_environment['subdomain']:
                    canvas_environment['subdomain']=''
                canvas_environment['domains'][environment]=''
        domain_validated=((canvas_environment['domains']['production']!='') and (canvas_environment['domains']['beta']!='') and (canvas_environment['domains']['test']!='')) or mode=='unattended'
    # Validate API Token
    apitoken_validated=False
    while (not apitoken_validated) and (canvas_environment['domains'][environment]!=''):
        # Prompt for API Token if not given
        if canvas_environment['api_token']=='' and mode!='unattended':
            canvas_environment['api_token']=str(input('Please enter your Canvas administrative API token: '))
        #Set HTTP headers for API calls
        get_headers={'Authorization' : 'Bearer ' + '%s' % canvas_api_token}
        put_headers={'Authorization' : 'Bearer ' + '%s' % canvas_api_token}
        url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/accounts'
        r = requestswithretry().get(url,headers=get_headers)
        if r.status_code==200:
            canvas_account=r.json()
            print(datetime.now().isoformat()+': API token validated, proceeding...')
            scriptlog+=datetime.now().isoformat()+': API token validated, proceeding...\n'
            apitoken_validated=True
            canvas_environment['account_ids']['root']=str(canvas_account[0]['id']) if canvas_account[0]['root_account_id']==None else str(canvas_account[0]['root_account_id'])
        else:
            print(datetime.now().isoformat()+': API token validation failed.  Token or domain settings are incorrect.')
            scriptlog+=datetime.now().isoformat()+': API token validation failed.  Token or domain settings are incorrect.\n'
            canvas_environment['api_token']=''
            if mode=='unattended':
                apitoken_validated=True
    # Prompt for Canvas Account ID
    # Get account list from Canvas
    account_id_validated=False
    canvas_accounts_dict={}
    if canvas_environment['domains'][environment]!='':
        all_accounts_ids_validated=True
        for account in canvas_environment['account_ids'].keys():
            account_id_validated=False
            while (not account_id_validated and all_accounts_ids_validated):
                if account=='root':
                    account_id_validated=True
                else:
                    if canvas_environment['account_ids'][account]=='' and mode=='unattended':
                        canvas_environment['account_ids'][account]=canvas_environment['root_account_id']
                        account_id_validated=True
                    else:
                        if canvas_accounts_dict=={}:
                            # Get account list from Canvas if not populated yet
                            url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/accounts'
                            ro=[]
                            ro=canvas_get_allpages(url,get_headers)
                            rosubs=[]
                            for i in range(len(ro)):
                                canvas_accounts_dict[str(ro[i]['name'])]=str(ro[i]['id'])
                                url2='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/accounts/'+str(ro[i]['id'])+'/sub_accounts?recursive=true'
                                ro2=[]
                                ro2=canvas_get_allpages(url2,get_headers)
                                for j in range(len(ro2)):
                                    canvas_accounts_dict[str(ro2[j]['name'])]=str(ro2[j]['id'])
                        # Prompt for ID selection
                        if canvas_environment['account_ids'][account]=='' and mode!='unattended':
                            canvas_environment['account_ids'][account]=input('What is the id number for the '+account+' account: # or [L]ist)? ')
                        if canvas_environment['account_ids'][account]=='L' or canvas_environment['account_ids'][account]=='l':
                            for item in canvas_accounts_dict:
                                print(canvas_accounts_dict[item]+': '+item)
                            canvas_environment['account_ids'][account]=input('What is the id number for the '+account+' account? ')
                        if canvas_environment['account_ids'][account] in canvas_accounts_dict.values():
                            print(datetime.now().isoformat()+': '+account+' account selection validated, proceeding...')
                            account_id_validated=True
                        else:
                            print(datetime.now().isoformat()+': invalid '+account+' account selection, please try again.')
                            canvas_environment['account_ids'][account]=''
                            if mode=='unattended':
                                account_id_validated=True
            if canvas_environment['account_ids'][account]=='':
                all_accounts_ids_validated=False
    return (canvas_environment['working_environment']!='') and (canvas_environment['domains'][canvas_environment['working_environment']]!='') and (canvas_environment['subdomain']!='') and (canvas_environment['api_token']!='') and (all_accounts_ids_validated);

start_time = datetime.now()
canvas_environment = {'api_token':canvas_api_token, 'subdomain':canvas_subdomain, 'working_environment':canvas_environment, 'domains':{'production':canvas_production_vanity_domain, 'test':canvas_test_vanity_domain, 'beta':canvas_beta_vanity_domain}, 'account_ids':{'root':'', 'working':canvas_account_id}}
if (not validate_canvas_environment(canvas_environment)):
    print('Canvas environment validation failed.  Exiting Script.')
else:
    start_time = datetime.now()
    # Get LTI list from Canvas
    url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/accounts/'+canvas_environment['account_ids']['working']+'/external_tools'
    ro=[]
    ro=canvas_get_allpages(url,get_headers)
    lti_dict={}
    for i in range(len(ro)):
        if ro[i]['course_navigation']!=None:
            lti_dict[str(ro[i]['id'])]=i
    # Prompt for LTI selection
    selection=False
    while (not selection):
        for item in lti_dict:
            print(item+': '+ro[lti_dict[item]]['name'])
        canvas_source_lti_id=input('Which LTI is the original/source from which visibility will be mimiced (enter the id number)? ')
        if canvas_source_lti_id in lti_dict.keys():
            selection=True
            lti_dict.pop(canvas_source_lti_id)
        else:
            print('Invalid selection, please try again.')
    selection=False
    while (not selection):
        for item in lti_dict:
            print(item+': '+ro[lti_dict[item]]['name'])
        canvas_target_lti_id=input('Which LTI should the visibility settings and position from source be mimiced to (enter the id number)? ')
        if canvas_target_lti_id in lti_dict.keys():
            selection=True
        elif canvas_target_lti_id==canvas_course_lti_id:
            print('Source and Target cannot be the same LTI, please try again.')
        else:
            print('Invalid selection, please try again.')

    start_time = datetime.now()

    # Iterate through courses and update target tab to source tab
    print('Getting course list...',end='\r')
    url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/accounts/'+canvas_environment['account_ids']['working']+'/courses'
    canvas_course_list=[]
    canvas_course_list=canvas_get_allpages(url,get_headers)
    if canvas_course_list:
        print('Getting course list... Retrieved',len(canvas_course_list),'courses.')
        print('Processing courses... ',end='\r')
        for course_index, course in enumerate(canvas_course_list, start=1):
            print('Processing courses... Course '+str(course['id'])+' ('+str(course_index)+'/'+str(len(canvas_course_list))+') ',end='\r')
            url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/courses/'+str(course['id'])+'/tabs'
            canvas_course_tabs_list=[]
            canvas_course_tabs_list=canvas_get_allpages(url,get_headers)
            source_tab={}
            target_tab={}
            for tab in canvas_course_tabs_list:
                if tab['id']=='context_external_tool_'+canvas_source_lti_id:
                    source_tab=tab
                if tab['id']=='context_external_tool_'+canvas_target_lti_id:
                    target_tab=tab
            if not ('hidden' in source_tab.keys() and 'hidden' in target_tab.keys()):
                if abs(int(source_tab['position'])-int(target_tab['position']))>1 or (('hidden' in source_tab.keys())!=('hidden' in target_tab.keys())):
                    update_params={'position' : int(source_tab['position'])+1, 'hidden' : 'hidden' in source_tab.keys()}
                    url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/courses/'+str(course['id'])+'/tabs/'+str(target_tab['id'])
                    r=requestswithretry().put(url,headers=put_headers,data=update_params)
                    if r.status_code==200:
                        print('Successfully updated '+str(course['id'])+': '+course['name'])
                        print('     ',update_params)
                    else:
                        print('Error',r.status_code,'when attempting to update update',str(course['id'])+':',course['name'])
                print('')
    else:
        print('Getting course list... Error!')
print('Finished!  Run time:',str(datetime.now() - start_time))

if mode!='unattended':
    input("Press Enter to continue...")
