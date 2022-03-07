# LocateYourMoney-Server
### Abstract
This is a small project for my 2021/2022 winter vacation, to keep track of my accounts' balance every day and give some charts to have a better understanding about how my money is distributed.
### Server: Data pipeline
This repository is where user's balances tracking is executed and updated to my gdrive folder. The main idea is to fetch the old log data, adding new balances record to log and update. Updates of bank accounts are realized by selenium webdriver (undetected chromedriver), and crypto exchange accounts updates are made with the connection to apis. The manipulation of user's information is another part of this project(LocateYourMoney-GUI).
### Things not accomplished
The ultimate goal is to deploy this script to a cloud server to run and update routinely, now it can only work on local with compiler executing the script. The server I chose was GCP. However, with the use of selenium, this may need a docker container to have it execute on cloud run. This is beyond my knowledge and skill-sets. May try to finish this sometimes in the future.
### References
The max exchange api part is mainly from: https://github.com/kulisu/max-exchange-api-python3. The web scrapping with undetected chrome driver is from: https://github.com/ultrafunkamsterdam/undetected-chromedriver. Much thanks to these amazing developers.
