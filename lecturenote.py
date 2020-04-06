#!/usr/bin/env python

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
import json
import os
import img2pdf
import logging
import shutil
import sys

mode = os.getenv("MODE")
TOKEN = os.getenv("TOKEN")

updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

imagenames = []

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=100,
    pool_maxsize=100)
session.mount('http://', adapter)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

if mode == "dev":
    def run(updater):
        updater.start_polling()
elif mode == "prod":
    def run(updater):
        PORT = int(os.environ.get("PORT", "8443"))
        HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
        # Code from https://github.com/python-telegram-bot/python-telegram-bot/wiki/Webhooks#heroku
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN)
        updater.bot.set_webhook("https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, TOKEN))
else:
    logger.error("No MODE specified!")
    sys.exit(1)


def lecture(update, context):
	
	url = update.message.text.split()[-1]
	
	noteid = begin(url)
	
	global dirName
	global imagenames
	
	detailURL = "https://lecturenotes.in/material/v1/" + str(noteid) + "/details"
	response = session.get(detailURL)
	details = response.json()
	dirName = details["material"]["name"]
	totalPage = details["material"]["pagesCount"]
	
	detail = "Title: " + str(dirName) +"\nPage: " + str(totalPage)
	print(detail)
	msg =  update.message.reply_text(detail)
	for i in range(1,totalPage+1):	
		url = "https://lecturenotes.in/material/v2/" + str(noteid) + "/page-" + str(i)
		response = session.get(url)
		#If 404 occurs end of Note reached
		if response.status_code == 404:
			return
		data = response.json()

		createDir(dirName)

		#This block of code gets path for the images
		for j in data["page"]:
			#Ignoring some prime feature hence some pages will not be available
			if j["upgradeToPrime"] == True:
				continue
			else:
				getImage(j["path"],dirName,j["pageNum"])
				if j["pageNum"]%25 == 0:
					msg.edit_text(detail + "\nStatus: " + str(j["pageNum"]) + " out of " + str(totalPage) + " pages done!")
		makePDF(dirName)
	
	msg.edit_text(detail + "\nEnjoy!")
	context.bot.send_document(chat_id=update.message.chat_id, document=open(floc, 'rb'),timeout = 120)
	shutil.rmtree(dirName)
	imagenames.clear()
	print("Success")

def begin(url):
	noteid = url.split('/')[4].split('-')[0]
	return noteid

def createDir(dirName):
	if not os.path.exists(dirName):
		os.makedirs(dirName + '/Images')
		os.makedirs(dirName + '/PDF')


def getImage(pic,dirName,i):
	#This block of code downloads images from the path locally
	pageLinks = "https://lecturenotes.in" + pic
	r = session.get(pageLinks)
	print(i)
	with open(dirName + '/Images/' + str(i) + '.jpeg', 'wb') as f:
		f.write(r.content)
		f.close()
	imagenames.append(dirName + '/Images/' + str(i) + '.jpeg')


def makePDF(dirName):
	global floc
	#This block of code converts the downloaded images to PDF
	with open(dirName + '/PDF/' + dirName + ".pdf","wb") as f:
		f.write(img2pdf.convert(imagenames))
		f.close()
	floc = dirName + '/PDF/' + dirName + ".pdf"

if __name__ == "__main__":

	# link = "https://lecturenotes.in/materials/25470-dbms"
	# begin(link)
	lecture_handler = CommandHandler('lecture', lecture)
	dispatcher.add_handler(lecture_handler)
	run(updater)