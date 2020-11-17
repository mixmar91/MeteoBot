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

HEADERS = ({'User-Agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36','Accept-Language': 'en-US, en;q=0.5'})

# meteo text to emoji dictionary
meteoEmojiDictionary = {
  "ΚΑΘΑΡΟΣ ": ":cleard:,:clearn:",
  "ΛΙΓΑ ΣΥΝΝΕΦΑ ": ":fewcloudsd:,:fewcloudsn:",
  "ΑΡΚΕΤΑ ΣΥΝΝΕΦΑ ": ":partlycloudyd:,:partlycloudyn:",
  "ΑΡΑΙΗ ΣΥΝΝΕΦΑ ": ":thincloudsd:,:thincloudsn:",
  "ΠΕΡΙΟΡΙΣΜΕΝΗ ΟΡΑΤΟΤΗΤΑ ": ":fog1:",
  "ΣΥΝΝΕΦΙΑΣΜΕΝΟΣ ": ":cloudy:",
  "ΑΣΘΕΝΗΣ ΒΡΟΧΗ ": ":lightrain:",
  "ΒΡΟΧΗ ": ":rain:",
  "ΚΑΤΑΙΓΙΔΑ ": ":storm:",
  "ΧΙΟΝΙ ": ":snow:"
}

# read config json file
with open('meteoConfig.json') as f:
  configJson = json.load(f)

# list with every possible hour of day
hourDayList = ["08:00", "11:00","14:00","17:00"]

def sendForecastReport(url, numberOfDataToSend):
    try:
        # request data from url
        page = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(page.content, features="lxml")

        # get a list of days
        days = (soup.find("div", id="prognoseis").find_all("td", class_="forecastDate"))
        dayListCounter = 0
        printDate = True

        # get a list of forecast data
        prognostika = (soup.find("div", id="prognoseis").find_all("tr", class_="perhour rowmargin"))

        # declare a counter to send only the 8 rows from the beginning
        sendMessageCounter = 0

        # declare a variable for the forecast report
        forecastReport = ""

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
            
            # create a message with above info
            message = hour + "\t" + temp+ "\t" + text

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
 
            # add row with the current forecast to the existing report
            forecastReport+=(message+'\n')

            # if the current hour is 23:00, then we should send the new date before we continue
            if hour == "23:00":
                printDate = True
            
            # increase the counter and stop the loop if we sent the first 8 rows 
            sendMessageCounter+=1
            if sendMessageCounter == numberOfDataToSend:
                break

        # send the forecast report as one message to the slack channel
        slack.sendSlackMessage(configJson['LogBotToken'], configJson['TestChannel'],report)
    except:
        e = sys.exc_info()[0]
        slack.sendSlackMessage(configJson['ErrorBotToken'], configJson['LoggingChannel'],e)


if __name__ == '__main__':
    url = 'https://www.meteo.gr/cf.cfm?city_id=89'
    numberOfDataToSend = 8
    sendForecastReport(url,numberOfDataToSend)
