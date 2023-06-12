################################################################################
################################################################################
## Canvas set course participation to term                                    ##
##                                                                            ##
##                                                                            ##
## Fill in the three variables directly below this header, then run with py   ##
## **Use at your own risk.  Please try changes in Test/Beta before Prod.**    ##
##                                                                            ##
## 2023 Christopher M. Casey (cmcasey79@hotmail.com)                          ##
################################################################################
################################################################################
script_version='2023.06.06.00001public'

# Script mode setup
# set as '' for deault operation, 'unattended' to run without prompts using the info below, 'verbose' for more detailed screen progress output, 'silent' to run without screen output, or 'silentunattended' or 'verboseunattended' to combine the options.
mode=''

# Canvas API token setup
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
# set these variables as the account/subaccount id you'd like to work in.
canvas_account_id=''

# Canvas environment setup
# set this variable as production, test, beta or leave as '' to prompt if not running in unattended mode
canvas_environment=''

################################################################################
################################################################################
## No changes to below code should be necessary.                              ##
################################################################################
################################################################################

import re
import socket
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
from io import StringIO
import json
from datetime import datetime, timedelta
import time
from dateutil.relativedelta import relativedelta
import csv
import collections
import smtplib
from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import make_msgid
def makehash():
    return collections.defaultdict(makehash)

scriptlog=''

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
# Returns a list of all items from all pages of a paginated API call
# Last updated 2023-05-16
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
# Last updated 2023-04-17.
def validate_canvas_environment(canvas_environment, validate_environments=None):
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
                    canvas_environment['domains'][environment]=input('Please enter your '+environment+' Canvas vanity domain (hit enter if you do not have one)')
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
        get_headers={'Authorization' : 'Bearer ' + '%s' % canvas_api_token}
        put_headers={'Authorization' : 'Bearer ' + '%s' % canvas_api_token}
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
    return (canvas_environment['working_environment']!='') and (canvas_environment['domains'][canvas_environment['working_environment']]!='') and (canvas_environment['subdomain']!='') and (canvas_environment['api_token']!='') and all_accounts_ids_validated and domain_validated;

hostname=socket.gethostname()
IPAddr=socket.gethostbyname(hostname)
print('Running script version '+script_version+' on '+hostname+', '+IPAddr)
scriptlog+='Running script version '+script_version+' on '+hostname+', '+IPAddr+'\n'
start_time = datetime.now()

# If script is running on ITS server, override some manually set values
if script_version[-3:]=='its':
    # get canvas-banner api token from ITS secure site
    if canvas_api_token=='':
        ITS_PasswordURL='https://passwordstate.it.umich.edu/api/passwords/7910'
        ITS_PasswordHeader= {'APIKey':'ef3d4c23a75986bf33a4e8752cb69df3'}
        ITS_PasswordResponse = requestswithretry().get(url = ITS_PasswordURL, headers = ITS_PasswordHeader)
        if ITS_PasswordResponse.status_code==200:
            ITS_PasswordJSON=ITS_PasswordResponse.json()
            #remove the "Authorization: Bearer " prefix, from password.
            canvas_api_token=ITS_PasswordJSON[0]["Password"][len("Authorization: Bearer "):] #Banner Account Token
    # set email options to use umich unsecured relay
    email_smtpservername='relay.mail.umich.edu'
    email_secureport=587
    email_authrequired=False

canvas_environment = {'api_token':canvas_api_token, 'subdomain':canvas_subdomain, 'working_environment':canvas_environment, 'domains':{'production':canvas_production_vanity_domain, 'test':canvas_test_vanity_domain, 'beta':canvas_beta_vanity_domain}, 'account_ids':{'root':'', 'working':canvas_account_id}}
if (not validate_canvas_environment(canvas_environment)):
    print('Canvas environment validation failed.  Exiting Script.')
    scriptlog+='Canvas environment validation failed.  Exiting Script.\n'
else:
    start_time = datetime.now()
    #Set HTTP headers for API calls
    get_headers={'Authorization' : 'Bearer ' + '%s' % canvas_environment['api_token']}
    put_headers={'Authorization' : 'Bearer ' + '%s' % canvas_environment['api_token']}
    delete_headers={'Authorization' : 'Bearer ' + '%s' % canvas_environment['api_token']}
    # Get term list from Canvas
    url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/accounts/'+str(canvas_environment['account_ids']['root'])+'/terms'
    canvas_term_list=[]
    canvas_term_list=canvas_get_allpages(url,get_headers)
    # Iterate through terms and proceed to update course options and publish as necessary for current or future courses
    if mode[0:6]!='silent': print('\nVerifying and updating by term...')
    scriptlog+='\nVerifying and updating by term...'
    for term in canvas_term_list:
        # only work with past terms    
        if term['end_at']!=None and datetime.fromisoformat(term['end_at'].replace('Z',''))<datetime.utcnow():
            if mode[0:6]!='silent': print('  '+term['name']+':')
            scriptlog+='\n  '+term['name']+':\n'
            if mode[0:6]!='silent': print('    Getting course list...',end='\r')
            url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/accounts/'+str(canvas_environment['account_ids']['working'])+'/courses?enrollment_term_id='+str(term['id'])+'&include[]=indexed'
            canvas_course_list=[]
            canvas_course_list=canvas_get_allpages(url,get_headers)
            if mode[0:6]!='silent': print('    Getting course list... Retrieved '+str(len(canvas_course_list))+' courses.')
            scriptlog+='    Getting course list... Retrieved '+str(len(canvas_course_list))+' courses.\n'
            scriptlog+='    Validating and updating course dates...\n'
            # iterate through all courses in the given term
            for course_index, course in enumerate(canvas_course_list, start=1):
                if mode[0:7]=='verbose': print('    Validating and updating course dates... Course '+str(course['id'])+' ('+str(course_index)+'/'+str(len(canvas_course_list))+') ',end='\r')
                # find undesired settings and update them as needed
                do_course_update=False
                updated_parameters=[]
                if course['restrict_enrollments_to_course_dates']==True:
                    course['restrict_enrollments_to_course_dates']=False
                    updated_parameters.append('restrict_enrollments_to_course_dates:false')
                    do_course_update=True
                if not (course['start_at']==None or course['start_at']==term['start_at']):
                    if mode[0:6]!='silent': print('\n      ***ALERT*** '+course['name']+' (canvas_course_id: '+str(course['id'])+') is '+course['workflow_state']+' and has modified start date: '+course['start_at'])
                    scriptlog+='      ***ALERT*** '+course['name']+' (canvas_course_id: '+str(course['id'])+') is '+course['workflow_state']+' and has modified start date: '+course['start_at']+'\n'
                    do_course_update=True
                    course['start_at']=None
                if course['end_at']!=None:
                    if mode[0:6]!='silent': print('\n      ***ALERT*** '+course['name']+' (canvas_course_id: '+str(course['id'])+') is '+course['workflow_state']+' and has modified end date: '+course['end_at'])                 
                    scriptlog+='      ***ALERT*** '+course['name']+' (canvas_course_id: '+str(course['id'])+') is '+course['workflow_state']+' and has modified end date: '+course['end_at']+'\n'                 
                    course['end_at']=None
                    do_course_update=True
                    updated_parameters.append('end_at:null')
                    #temp to fix old data
                    #if course['workflow_state']=='unpublished':
                    #    course['workflow_state']='available'
                if do_course_update:
                    # update course settings if needed
                    url='https://'+canvas_environment['domains'][canvas_environment['working_environment']]+'/api/v1/courses/'+str(course['id'])
                    r=requestswithretry().put(url,headers=put_headers,json={'course':course,'offer':True if 'workflow_state:available' in updated_parameters else False})
                    if r.status_code==200:
                        if mode[0:6]!='silent': print('\n      '+course['name']+' (canvas_course_id: '+str(course['id'])+') successfully updated:\n        '+'\n        '.join(map(str, updated_parameters)))
                        scriptlog+='      '+course['name']+' (canvas_course_id: '+str(course['id'])+') successfully updated:\n        '+'\n        '.join(map(str, updated_parameters))+'\n'
                    else:
                        print('\n      ***ALERT*** '+datetime.now().isoformat()+': Error '+str(r.status_code)+' when attempting to update '+course['name']+' (canvas_course_id: '+str(course['id'])+') at '+url)
                        scriptlog+='      ***ALERT*** '+datetime.now().isoformat()+': Error '+str(r.status_code)+' when attempting to update '+course['name']+' (canvas_course_id: '+str(course['id'])+') at '+url+'\n'
            if mode[0:6]!='silent': print('    Validating and updating course dates... ('+str(len(canvas_course_list))+'/'+str(len(canvas_course_list))+') complete.     ')
            scriptlog+='    Validating and updating course dates... ('+str(len(canvas_course_list))+'/'+str(len(canvas_course_list))+') complete.\n'

print('Finished!  Run time: '+str(datetime.now() - start_time))
scriptlog+='\nFinished!  Run time:'+str(datetime.now() - start_time)+'\n'

if mode[-10:]!='unattended':
    input("Press Enter to continue...")
