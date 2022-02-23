# -*- coding: utf-8 -*-
"""
Created on Wed Feb  2 20:31:36 2022

@author: user
"""
import base64
import hashlib
import json
from urllib.parse import urlencode
from urllib.request import Request as rq
from urllib.request import urlopen
import time
import hmac
from requests import Request, Session, post
from selenium.webdriver.common.by import By
from time import sleep
import undetected_chromedriver as uc
import io

import httplib2
from oauth2client.client import flow_from_clientsecrets, AccessTokenCredentials
from oauth2client.file import Storage
from oauth2client.tools import run_flow

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload

PUBLIC_API_URL = 'https://max-api.maicoin.com/api'
PRIVATE_API_URL = 'https://max-api.maicoin.com/api'
    
PUBLIC_API_VERSION = 'v2'
PRIVATE_API_VERSION = 'v2'
    
def get_current_timestamp():
    return int(round(time.time() * 1000))

class Client(object):
    def __init__(self, key, secret, timeout=30):
        self._api_key = key
        self._api_secret = secret

        self._api_timeout = int(timeout)

    def _build_body(self, endpoint, query=None):
        if query is None:
            query = {}

        # TODO: duplicated nonce may occurred in high frequency trading
        # fix it by yourself, hard code last two characters is a quick solution
        # {"error":{"code":2006,"message":"The nonce has already been used by access key."}}
        body = {
            'path': f"/api/{PRIVATE_API_VERSION}/{endpoint}.json",
            'nonce': get_current_timestamp(),
        }

        body.update(query)

        return body

    def _build_headers(self, scope, body=None):
        if body is None:
            body = {}

        headers = {
            'Accept': 'application/json',
            'User-Agent': 'pyCryptoTrader/1.0.3',
        }

        if scope.lower() == 'private':
            payload = self._build_payload(body)
            sign = hmac.new(bytes(self._api_secret, 'utf-8'), bytes(payload, 'utf-8'), hashlib.sha256).hexdigest()

            headers.update({
                # This header is REQUIRED to send JSON data.
                # or you have to send PLAIN form data instead.
                'Content-Type': 'application/json',
                'X-MAX-ACCESSKEY': self._api_key,
                'X-MAX-PAYLOAD': payload,
                'X-MAX-SIGNATURE': sign
            })

        return headers

    def _build_payload(self, body):
        return base64.urlsafe_b64encode(json.dumps(body).encode('utf-8')).decode('utf-8')

    def _build_url(self, scope, endpoint, body=None, query=None):
        if query is None:
            query = {}

        if body is None:
            body = {}

        # 2020-03-03 Updated
        # All query parameters must equal to payload
        query.update(body)

        if scope.lower() == 'private':
            url = f"{PRIVATE_API_URL}/{PRIVATE_API_VERSION}/{endpoint}.json"
        else:
            url = f"{PUBLIC_API_URL}/{PUBLIC_API_VERSION}/{endpoint}.json"

        return f"{url}?{urlencode(query, True, '/[]')}" if len(query) > 0 else url

    def _send_request(self, scope, method, endpoint, query=None, form=None):
        if form is None:
            form = {}

        if query is None:
            query = {}

        body = self._build_body(endpoint, query)
        data = None

        if len(form) > 0:
            body.update(form)
            data = json.dumps(body).encode('utf-8')

        # Build X-MAX-PAYLOAD header first
        headers = self._build_headers(scope, body)

        # Fix "401 Payload is not consistent .."
        # state[]=cancel&state[]=wait&state[]=done
        # {"path": "/api/v2/orders.json", "state": ["cancel", "wait", "done"]}
        for key in body:
            if type(body[key]) is list and not key[-2:] == '[]':
                body[f"{key}[]"] = body.pop(key)

                if key in query:
                    query.pop(key)

        # Build final url here
        url = self._build_url(scope, endpoint, body, query)

        request = rq(headers=headers, method=method.upper(), url=url.lower())

        # Start: Debugging with BurpSuite only
        # import ssl
        # ssl._create_default_https_context = ssl._create_unverified_context

        """
        root@kali:/tmp/max-exchange-api-python3# export HTTPS_PROXY=https://127.0.0.1:8080
        root@kali:/tmp/max-exchange-api-python3# /usr/bin/python3 all_api_endpoints.py
        """
        # End: Debugging with BurpSuite only

        response = urlopen(request, data=data, timeout=self._api_timeout)

        return json.loads(response.read())

    def get_private_account_balances(self):
        
        return self._send_request('private', 'GET', 'members/accounts')

    def get_public_all_tickers(self, pair=None):

        if pair is not None and len(pair) > 0:
            return self._send_request('public', 'GET', f"tickers/{pair.lower()}")
        else:
            return self._send_request('public', 'GET', 'tickers')


def api_ftx(key, secret):
    
    API_KEY = key
    API_SECRET = secret
    
    method = 'wallet/all_balances'
    endpoint = 'https://ftx.com/api/'

    ts = int(time.time() * 1000)
    request = Request('GET', endpoint+method)
    prepared = request.prepare()
    signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
    signature = hmac.new(API_SECRET.encode(), signature_payload, 'sha256').hexdigest()
    
    prepared.headers['FTX-KEY'] = API_KEY
    prepared.headers['FTX-SIGN'] = signature
    prepared.headers['FTX-TS'] = str(ts)
    
    S = Session()
    
    response = S.send(prepared)
    
    ftx_coin_dict = {}
    ftx_total_value = 0
    
    if response.json()['success'] == False:
        print("Ftx {}".format(response.json()['error']))
        return {}, 0
    
    for i in response.json()['result']['main']:
        key = i['coin']
        value = float(round(i['usdValue'], 2))
        if value != 0:
            update = {key:value}
            ftx_coin_dict.update(update)
            ftx_total_value += value

    return ftx_coin_dict, ftx_total_value

def api_max(key, secret):
     
    max_Key, max_Secret = key, secret

    client = Client(max_Key, max_Secret)
    result = client.get_private_account_balances()
            
    usdt = float(client.get_public_all_tickers('usdttwd')['last'])
            
    max_coin_dict = {}
    max_total_value = 0

    for i in result:
        key = i['currency']
        value = float(i['balance'])
        if key == 'twd':
            value = value/usdt
        if value != 0:
            update = {key:value}
            max_coin_dict.update(update)
            max_total_value += value

    return max_coin_dict, max_total_value

    

def ctbc_get(driver, ID, user, password0):
        
    url = 'https://www.ctbcbank.com/twrbc/twrbc-general/ot001/010'

    ctbc_id, ctbc_user, ctbc_pass = ID, user, password0

    driver.get(url)
  
    id_box_path = "/html/body/app/div[1]/div[2]/twrbc-general-ot001-010/div/div[2]/div[3]/div[1]/div/nav-tabs/div/div[1]/div[2]/form/div/div[1]/div/input" 
    
    try:

        while len(driver.find_elements(By.XPATH, id_box_path)) == 0:
            sleep(0.1)
        
        driver.find_element(By.XPATH, id_box_path).send_keys(ctbc_id)
        
        user_box_path = "/html/body/app/div[1]/div[2]/twrbc-general-ot001-010/div/div[2]/div[3]/div[1]/div/nav-tabs/div/div[1]/div[2]/form/div/div[2]/div/input"
        driver.find_element(By.XPATH, user_box_path).send_keys(ctbc_user)
            
        password_path = "/html/body/app/div[1]/div[2]/twrbc-general-ot001-010/div/div[2]/div[3]/div[1]/div/nav-tabs/div/div[1]/div[2]/form/div/div[3]/div/input"
        driver.find_element(By.XPATH, password_path).send_keys(ctbc_pass)
        
        login_path = "/html/body/app/div[1]/div[2]/twrbc-general-ot001-010/div/div[2]/div[3]/div[1]/div/nav-tabs/div/div[1]/div[2]/div/a[1]"
        driver.find_element(By.XPATH, login_path).click()
        sleep(2)
        ctbc_balance_path = "/html/body/app/div[1]/div[2]/twrbc-home-qu000-010/div/div/nav-tabs-overview/div/ul/li[1]/a/span"
        ctbc_balance = driver.find_element(By.XPATH, ctbc_balance_path)

    except:
        print('Failed to login CTBC account. Please try again.')
        return 0
        
    try:

        ctbc_balance = int(ctbc_balance.text.replace(',', '') )
        
        logout_path = "/html/body/app/div[1]/ib-header/div/header/div/div/div[3]/ul/li[4]/div/a[2]"
        driver.find_element(By.XPATH, logout_path).click()
        
        sleep(0.5)
        confirm_path = "/html/body/app/modal-confirm[2]/div/div/div/div[3]/a[1]"
        driver.find_element(By.XPATH, confirm_path).click()
        
        
        return ctbc_balance
    
    except:
        print('Failed to return remaining balance. Please try again')
        return 0

def esun_get(driver, ID, user, password0):
        
    url = 'https://ebank.esunbank.com.tw/index.jsp'

    esun_id, esun_user, esun_pass = ID, user, password0

    driver.get(url)
  
    id_box_path = "/html/body/div[1]/div[2]/div/div/div[4]/div[4]/form/div[1]/table/tbody/tr[2]/td[2]/input" 
    
    try:

        while len(driver.find_elements(By.XPATH, id_box_path)) == 0:
            sleep(0.1)
        
        driver.find_element(By.XPATH, id_box_path).send_keys(esun_id)
        
        user_box_path = "/html/body/div[1]/div[2]/div/div/div[4]/div[4]/form/div[1]/table/tbody/tr[3]/td[2]/input[3]"
        driver.find_element(By.XPATH, user_box_path).send_keys(esun_user)
            
        password_path = "/html/body/div[1]/div[2]/div/div/div[4]/div[4]/form/div[1]/table/tbody/tr[4]/td[2]/input"
        driver.find_element(By.XPATH, password_path).send_keys(esun_pass)
        
        login_path = "/html/body/div[1]/div[2]/div/div/div[4]/div[4]/form/div[1]/div[2]/a[3]"
        driver.find_element(By.XPATH, login_path).click()
        sleep(2)
        esun_balance_path = "/html/body/div/div[2]/div[2]/div/div/div[2]/div[4]/ul/li[1]/div[2]/form/table/tbody/tr[3]/td[3]"
        esun_balance = driver.find_element(By.XPATH, esun_balance_path)

    except:
        print('Failed to login Esun account. Please try again.')
        return 0
        
    try:

        esun_balance = int(esun_balance.text.replace(',', '') )
        
        logout_path = "/html/body/div/div[1]/div[2]/form/div[1]/div[3]/a"
        driver.find_element(By.XPATH, logout_path).click()
        
        return esun_balance
    
    except:
        print('Failed to return remaining balance. Please try again')
        return 0

def log_update(today_date, info):   
        
    crypto_accounts = {}
    bank_accounts = {}
            
    today_dict = {}
            
    for name, values in info.items():
                
        if values["Type"] == "Crypto":
            crypto_accounts.update({name:values})
        elif values["Type"] == "Bank":
            bank_accounts.update({name:values})
                    
    for name, values in crypto_accounts.items():
            
        if values["Provider"] == "Ftx":
                
            key = values["Login_info"]["API_KEY"]
            secret = values["Login_info"]["API_SECRET"]
            
            ftx_coin_dict, ftx_total_value = api_ftx(key, secret)
                
            today_dict.update({name+"_coin" : ftx_coin_dict})
            today_dict.update({name+"_total" : ftx_total_value})
                
                
        if values["Provider"] == "Max":
                
            key = values["Login_info"]["API_KEY"]
            secret = values["Login_info"]["API_SECRET"]
            
            max_coin_dict, max_total_value = api_max(key, secret)
            
            today_dict.update({name+"_coin" : max_coin_dict})
            today_dict.update({name+"_total" : max_total_value})
                
    for name, values in bank_accounts.items():
                
        driver = uc.Chrome(headless=True)
                
        if values["Provider"] == "Ctbc":
                    
            Id = values["Login_info"]["ID"]
            usercode = values["Login_info"]["User code"]
            password0 = values["Login_info"]["Password"]
              
            ctbc_balance = ctbc_get(driver, Id, usercode, password0)
                    
            today_dict.update({name+"_balance" : ctbc_balance})

        if values["Provider"] == 'Esun':
            
            Id = values['Login_info']['ID']
            usercode = values["Login_info"]["User code"]
            password0 = values["Login_info"]["Password"]

            esun_balance = esun_get(driver, Id, usercode, password0)

            today_dict.update({name+'_balance': esun_balance})
                    
                    
        driver.quit()

    today_log = {today_date:today_dict}
    
    
    return today_log





def refresh_access_token():
# You can also read these values from the json file
    client_id = "1046268304824-csvkaoqhip7ro82vd7tb7iffgvcq1l0v.apps.googleusercontent.com"
    client_secret = "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"
    refresh_token = "1//0eC2v3I-DgsBgCgYIARAAGA4SNwF-L9IrdIekaTpeHmid-fSuTpudtOxC0xy9A5Wa_yY7CvoZ-69bM_4tw8_scM7g6gE5yomeAls"
    params = {
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
        }

    authorization_url = "https://www.googleapis.com/oauth2/v4/token"

    r = post(authorization_url, data=params)

    if r.ok:
        return r.json()['access_token']
    else:
        return None



def get_credentials(access_token):
    user_agent = "Google Sheets API for Python"
    revoke_uri = "https://accounts.google.com/o/oauth2/revoke"
    credentials = AccessTokenCredentials(
                                    access_token=access_token,
                                    user_agent=user_agent,
                                    revoke_uri=revoke_uri)
    return credentials


def updateFile(file_name, file, file_id):

    access_token = refresh_access_token()

    credentials = get_credentials(access_token)
    http = credentials.authorize(httplib2.Http())
    drive_service = build('drive', 'v3', http=http)


    file_metadata = {
    'name': file_name,
    'mimeType': '*/*'
    }

    file = io.BytesIO(json.dumps(file).encode('utf-8'))
    media = MediaIoBaseUpload(file,
                              mimetype='*/*',
                              resumable=True)
    file = drive_service.files().update(body=file_metadata, 
                                        media_body=media,
                                        fileId =  file_id, 
                                        addParents = '1POG-erqU5swFWkI8t5TF-_-tOBVQELJ9', 
                                        fields='id, parents').execute()
    print ('File ID: ' + file.get('id'))


def getFile(local_file_name, file_id):

    access_token = refresh_access_token()

    credentials = get_credentials(access_token)
    http = credentials.authorize(httplib2.Http())
    drive_service = build('drive', 'v3', http=http)

    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("{} loaded {}%".format(local_file_name, status.progress() * 100))

    fh.seek(0)
    file = json.loads(fh.read().decode('utf-8'))
    fh.close()
    return file

def delete_one_log(date, name, file_id, update=True):

    log = getFile(name, file_id)
    for key, v in log.items():
        if date in v:
            v.pop(date)
            print('log found.')
    if update==True:
        updateFile(name, log, file_id)
        print('Deletion of {} completed.'.format(date))

# delete_one_log('2022/02/15', 'log.json', '1ARGlhdeMGqaJ1gGslbV1zWO9fFhnlsy3')



