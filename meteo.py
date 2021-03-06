import requests
from glob import glob
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from time import sleep
from lxml import html, etree
import slackAPI as slack
import json
import sys
from meteoStaticData import meteoRegionDict,meteoEmojiDictionary, hourDayList

HEADERS = ({'User-Agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36','Accept-Language': 'en-US, en;q=0.5'})

# counter variable to use it at showregions function
count = 0

# read config json file
with open('meteoConfig.json') as f:
  configJson = json.load(f)

def sendForecastReport(url, numberOfDataToSend):
    try:
        # request data from url
        page = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(page.content, features="lxml")

        # get the name of the selected city
        city = soup.find("h1", class_="cityname").get_text()
        
        # get a list of days
        days = (soup.find("div", id="prognoseis").find_all("td", class_="forecastDate"))
        dayListCounter = 0
        printDate = True

        # get a list of forecast data
        prognostika = (soup.find("div", id="prognoseis").find_all("tr", class_="perhour rowmargin"))

        # declare a counter to send only the 8 rows from the beginning
        sendMessageCounter = 0

        # declare a variable for the forecast report
        forecastReport = "*"+city+"*\n"

        # loop all the forecast data
        for p in prognostika:

            # send the date (if it is required)
            if printDate:
                # isolate the day from html item and add the * at the beginng to start the bold format
                day = "*"+days[dayListCounter].get_text().splitlines()[0].split(" ")[0].upper()

                # isolate the number of month from html
                numberOfMonth = ''.join(c for c in days[dayListCounter].get_text().splitlines()[0] if c.isdigit())

                # isolate the month from html and add the * to the end to terminate the bold format
                month = days[dayListCounter].find("span",class_="monthNumbercf").get_text().replace(" ","")+"*"

                # create a string with day, day-number and month
                dateText = " ".join([day,numberOfMonth,month])

                # add row with the date to the existing report
                forecastReport+=(dateText+'\n')
                dayListCounter+=1
                printDate = False

            # get the hour, temp and text from the forecast row
            hour = (p.find_all("td")[0].find_all("td")[0].get_text())
            temp =(p.find("td", class_="innerTableCell temperature tempwidth").find_all("div")[0].get_text()).splitlines()[0]
            text =(p.find("td", class_="innerTableCell PhenomenaSpecialTableCell phenomenafull").find_all("td")[0].get_text()).splitlines()[0]

            # add a zero in fron of temp to make it double digit if it is less than 10 degrees
            if len(temp)==3:
                temp='0'+temp

            # create a message with above info
            message = hour + "\t" + temp+ "\t"

            # check if we have emoji for the specific text and append it to the message
            if text in meteoEmojiDictionary:
                # some texts have different emoji for day and night
                if len(meteoEmojiDictionary[text].split(","))>1:
                    if hour in hourDayList:
                        message += "\t" +meteoEmojiDictionary[text].split(",")[0]
                    else:
                        message += "\t" +meteoEmojiDictionary[text].split(",")[1]
                else:
                    message += "\t" +meteoEmojiDictionary[text]
            else:
                logmessage = "Text "+text+" not found in dictionary."
                slack.sendSlackMessage(configJson['LogBotToken'], configJson['LoggingChannel'],logmessage)

            message += "\t" + text

            # add row with the current forecast to the existing report
            forecastReport+=(message+'\n')

            # if the current hour is 23:00, then we should send the new date before we continue
            if hour == "23:00":
                printDate = True

            # increase the counter and stop the loop if we sent the required rows
            sendMessageCounter+=1
            if sendMessageCounter == numberOfDataToSend:
                break

        # send the forecast report as one message to the slack channel
        slack.sendSlackMessage(configJson['MeteoBotToken'], configJson['MeteoChannel'],forecastReport)
    except:
        e = sys.exc_info()[0]
        slack.sendSlackMessage(configJson['ErrorBotToken'], configJson['LoggingChannel'],e)

def helpMe():
    slack.sendSlackMessage(configJson['MeteoBotToken'], configJson['MeteoChannel'],"How can i help you?")

def showRegions():
    # get region dict keys, which are the region names
    keys = meteoRegionDict.keys()

    # map them with a increment counter before the name
    result = map(addCounter, keys) 

    # create the respond message
    resp = "The available regions are : \n\t\t" + "\n\t\t".join((list(result)))
    slack.sendSlackMessage(configJson['MeteoBotToken'], configJson['MeteoChannel'],resp)

def addCounter(n): 
    global count
    count = count + 1
    return str(count) + ". " + n 

def showRegionCities(regionCounter):
    # check that region counter is valid
    if regionCounter>0 and regionCounter<len(meteoRegionDict.keys()):
        # get regions from dictionary
        keys=list(meteoRegionDict.keys())

        # get selected region
        region = keys[(regionCounter-1)]

        # create respond message
        resp = "The available cities of " +region+" are :"
        for k,v in sorted(meteoRegionDict[region].items()):
            # for each row add new line and two tabs righter
            resp+= '\n\t\t'
            # add city id and name
            resp+= ((' '*((3-len(v)+1)*2)).join((v,'\t'+k)))
    else:
        resp = "Invalid given region."
    slack.sendSlackMessage(configJson['MeteoBotToken'], configJson['MeteoChannel'],resp)

if __name__ == '__main__':
    if len(sys.argv)==4 and sys.argv[1]=="meteo":
        # get the first argument as city id
        cityId = sys.argv[2]

        # get the second argument as number of days to get the forecast
        daysToScrape = int(sys.argv[3])

        # create meteo url
        url= 'https://www.meteo.gr/cf.cfm?city_id='+cityId

        # each day have 8 row of data
        numberOfDataToSend = 8*daysToScrape

        # meteo have forecast data only for the next 5 days
        if numberOfDataToSend>43:
            numberOfDataToSend = 43

        # call function to scrape data from meteo
        sendForecastReport(url,numberOfDataToSend)
    elif len(sys.argv)==2 and sys.argv[1]=="helpme":
        helpMe()
    elif len(sys.argv)==2 and sys.argv[1]=="showregions":
        showRegions()
    elif len(sys.argv)==3 and sys.argv[1]=="showregioncities":
        showRegionCities(int(sys.argv[2]))
    else:
        url = 'https://www.meteo.gr/cf.cfm?city_id=89'
        numberOfDataToSend = 8
        # call function to scrape data from meteo
        sendForecastReport(url,numberOfDataToSend)
