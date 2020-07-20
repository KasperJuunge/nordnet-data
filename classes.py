import requests 
from datetime import datetime
from datetime import date
from password import user, password
import pandas as pd 


class Nordnet():
    """ Class to connect and pull finance data from nordnet.dk """
    def __init__(self):
        pass
    
    def _login(self):
        
        """ This method logs into Nordnet. It requires that username and password
        are imported from a separate file as user and password.
        
        Thanks to Morten Helmstedt who wrote the code used in this function. His
        code can be found on his website https://helmstedt.dk . """
    
        # Creates a dictionary to use with cookies  
        cookies = {}

        # First part of cookie setting prior to login
        url = 'https://classic.nordnet.dk/mux/login/start.html?cmpi=start-loggain&state=signin'
        request = requests.get(url)
        cookies['LOL'] = request.cookies['LOL']
        cookies['TUX-COOKIE'] = request.cookies['TUX-COOKIE']

        # Second part of cookie setting prior to login
        url = 'https://classic.nordnet.dk/api/2/login/anonymous'
        request = requests.post(url, cookies=cookies)
        cookies['NOW'] = request.cookies['NOW']

        # Actual login that gets us cookies required for later use
        url = "https://classic.nordnet.dk/api/2/authentication/basic/login"
        request = requests.post(url,cookies=cookies, data = {'username': user, 'password': password})
        cookies['NOW'] = request.cookies['NOW']
        cookies['xsrf'] = request.cookies['xsrf']

        # Getting a NEXT cookie
        url = "https://classic.nordnet.dk/oauth2/authorize?client_id=NEXT&response_type=code&redirect_uri=https://www.nordnet.dk/oauth2/"
        request = requests.get(url, cookies=cookies)
        cookies['NEXT'] = request.history[1].cookies['NEXT']

        return url, cookies
    
    
    def get_transactions(self, startdate='2020-06-11'):
        """ Download transactions from Nordnet depot to ./data .
        Args:
        - startdate: the start date for transaction history.

        Thanks to Morten Helmstedt who wrote the code used in this function. His
            code can be found on his website https://helmstedt.dk . """

        # Accounts
        accounts = {"Frie midler: Nordnet": "1"}

        # Start date (start of period for transactions) and date today used for extraction of transactions
        today = date.today()
        enddate = datetime.strftime(today, '%Y-%m-%d')

        # Manual data lines. These can be used if you have portfolios elsewhere that you would
        # like to add manually to the data set. If no manual data the variable manualdataexists
        # should be set to False
        manualdataexists = False
        manualdata = """   Id;Bogføringsdag;Handelsdag;Valørdag;Transaktionstype;Værdipapirer;Instrumenttyp;ISIN;Antal;Kurs;Rente;Afgifter;Beløb;Valuta;Indkøbsværdi;Resultat;Totalt antal;Saldo;Vekslingskurs;Transaktionstekst;Makuleringsdato;Verifikations-/Notanummer;Depot
        ;30-09-2013;30-09-2013;30-09-2013;KØBT;Obligationer 3,5%;Obligationer;;72000;;;;-69.891,54;DKK;;;;;;;;;;Frie midler: Finansbanken
        """

        # A variable to store transactions before saving to csv
        transactions = ""

        # Login to Nordnet
        url, cookies = self._login()


        # GET TRANSACTION DATA #

        # Payload and url for transaction requests
        payload = {
        'locale': 'da-DK',
        'from': startdate,
        'to': enddate,
        }

        url = "https://www.nordnet.dk/mediaapi/transaction/csv/filtered"

        firstaccount = True
        for portfolioname, id in accounts.items():
            payload['account_id'] = id
            data = requests.get(url, params=payload, cookies=cookies)
            result = data.content.decode('utf-16')
            result = result.replace('\t',';')

            result = result.splitlines()

            firstline = True
            for line in result:
                # For first account and first line, we use headers and add an additional column
                if line and firstline == True and firstaccount == True:
                    transactions += line + ';' + "Depot" + "\n"
                    firstaccount = False
                    firstline = False
                # First lines of additional accounts are discarded
                elif line and firstline == True and firstaccount == False:
                    firstline = False
                # Content lines are added
                elif line and firstline == False:
                    # Fix because Nordnet sometimes adds one empty column too many
                    if line.count(';') == 23:
                        line = line.replace('; ',' ')
                    transactions += line + ';' + portfolioname + "\n"

        # ADD MANUAL LINES IF ANY #
        if manualdataexists == True:
            manualdata = manualdata.split("\n",2)[2]
            transactions += manualdata

        # Saves CSV
        with open("./data/transactions.csv", "w", encoding='utf8') as fout:
            fout.write(transactions)
        
        

    def get_share_prices(self, sharelist, startdate='2013-01-01') :
        
        """ Download historical sharepirces from Nordnet and Morningstar.
            Args:
            - sharelist: list of shares to download. Each share should be representented by
                         a list in the following format [Name, Morningstar ID, Nordnet ID]
            - startdate: the start date for historical prices.

            Thanks to Morten Helmstedt who wrote the code used in this function. His
            code can be found on his website https://helmstedt.dk . """

        # Initialize
        finalresult = "" # variable to store historical prices before saving to csv
        finalresult += '"date";"price";"share"' + '\n'
        cookies = {} # dictionary for storing cookies

        # Login to Nordnet
        url, cookies = self._login()

        
        # LOOPS TO REQUEST HISTORICAL PRICES AT NORDNET AND MORNINGSTAR #
        # Nordnet loop to get historical prices
        for share in sharelist:
            # Nordnet stock identifier and market number must both exist
            if share[2]:
                url = "https://www.nordnet.dk/api/2/instruments/historical/prices/" + str(share[2])
                payload = {"from": startdate, "fields": "last"}
                data = requests.get(url, params=payload, cookies=cookies)
                jsondecode = data.json()

                # Sometimes the final date is returned twice. A list is created to check for duplicates.
                datelist = []

                for value in jsondecode[0]['prices']:
                    price = str(value['last'])
                    price = price.replace(".",",")
                    date = datetime.fromtimestamp(value['time'] / 1000)
                    date = datetime.strftime(date, '%Y-%m-%d')
                    # Only adds a date if it has not been added before
                    if date not in datelist:
                        datelist.append(date)
                        finalresult += '"' + date + '"' + ";" + '"' + price + '"' + ";" + '"' + share[0] + '"' + "\n"

        # Morningstar loop to get historical prices         
        for share in sharelist:
            # Only runs for one specific fund in this instance
            if share[0] == "Nordnet Superfonden Danmark":
                payload = {"id": share[1], "currencyId": "DKK", "idtype": "Morningstar", "frequency": "daily", "startDate": startdate, "outputType": "COMPACTJSON"}
                data = requests.get("http://tools.morningstar.dk/api/rest.svc/timeseries_price/nen6ere626", params=payload)
                jsondecode = data.json()

                for lists in jsondecode:
                    price = str(lists[1])
                    price = price.replace(".",",")
                    date = datetime.fromtimestamp(lists[0] / 1000)
                    date = datetime.strftime(date, '%Y-%m-%d')
                    finalresult += '"' + date + '"' + ";" + '"' + price + '"' + ";" + '"' + share[0] + '"' + "\n"

                    
        # Write to CSV file
        with open("./data/prices.csv", "w", newline='', encoding='utf8') as fout:
            fout.write(finalresult)