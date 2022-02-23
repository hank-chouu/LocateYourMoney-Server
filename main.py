# -*- coding: utf-8 -*-
"""
Created on Sun Jan 30 15:36:43 2022

@author: user
"""

import os.path
import json
from datetime import date
from functions import getFile, log_update, updateFile, getFile
import time

log_file_id = '1ARGlhdeMGqaJ1gGslbV1zWO9fFhnlsy3'
user_file_id = '1obX_BMPSTeL-VeG8pjuLOKPFXunFiio1'

def main(update = True):
    user = getFile('user.json', user_file_id)
    log = getFile('log.json', log_file_id)
       
            
    # update if needed
    
    today_date = date.today().strftime("%Y/%m/%d")
    
    for name, user_info in user.items():
        
        if not name in log:
            
            start_time = time.time()
            log.update({name:log_update(today_date, user_info["info"])})
            print("{}: user {} initialized. Time spent: {} secs.".format(today_date, name, round((time.time() - start_time), 2)))
                
        else:
            
            if not today_date in log[name]:
            
                start_time = time.time()
                log[name].update(log_update(today_date, user_info['info']))
                print("{}: user {} update completed. Time spent: {} secs.".format(today_date, name, round((time.time() - start_time), 2)))
            else:
                print("{}: user {} has no need of an update.".format(today_date, name))
    if update == True:
        updateFile('log.json', log, log_file_id)
        print('Log uploaded to google drive succeeded.')

if __name__ == '__main__':

    main(update=True)
    
    
    
    


            
    
    
        
        
        
    



    
