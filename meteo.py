import requests
from glob import glob
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from time import sleep
from lxml import html, etree
import slackAPI as slack
import json

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
  "ΧΙΟΝΙ ": ":snow:",

}

# read config json file
with open('meteoConfig.json') as f:
  configJson = json.load(f)

# list with every possible hour of day
hourDayList = ["08:00", "11:00","14:00","17:00"]

def sendForecastReport(url, numberOfDataToSend):
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

    # loop all the forecast data
    for p in prognostika:
        
        # send the date (if it is required) 
        if printDate:
            slack.sendSlackMessage(configJson['MeteoBotToken'], configJson['TestChannel'],days[dayListCounter].get_text().splitlines()[0])
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
        
        # send message with forect row to slack channel
        slack.sendSlackMessage(configJson['MeteoBotToken'], configJson['MeteoChannel'],message)

        # if the current hour is 23:00, then we should send the new date before we continue
        if hour == "23:00":
            printDate = True
        
        # increase the counter and stop the loop if we sent the first 8 rows 
        sendMessageCounter+=1
        if sendMessageCounter == numberOfDataToSend:
            break


if __name__ == '__main__':
    url = 'https://www.meteo.gr/cf.cfm?city_id=89'
    numberOfDataToSend = 8
    sendForecastReport(url,numberOfDataToSend)