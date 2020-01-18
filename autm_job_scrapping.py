from langdetect import detect
import re
import gspread
from gspread_pandas import Spread, Client, conf
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
import requests
from bs4 import BeautifulSoup

# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client = gspread.authorize(creds)
c = conf.get_config(r'C:\Users\SYDNEY\AppData\Local\Programs\Python\Python38\Scripts','client_secret.json') #For gspread_pandas

def scrap_job_data(page_url):
	#input: page url
	#output: Dataframe containing the data scrapped from the page
	df = pd.DataFrame(columns=('url', 'job title', 'company', 'description'))
	row = [0,0, 0, 0]
	page = requests.get(page_url)
	soup = BeautifulSoup(page.content, 'html.parser')
	all_paid_jobs = soup.find_all(class_='PaidJob')
	all_other_jobs = soup.find_all(class_='jix_robotjob')
	
	for i in range(len(all_paid_jobs)):
		row[1], row[2] = all_paid_jobs[i].select('a b')[0].text, all_paid_jobs[i].select('a b')[1].text #Get job title and compay name
		row[0] = all_paid_jobs[i].select('a b')[0].parent['href']   #Some ads have a picture, some don't, but the url is always in the parent tag of the job title, that's how we get it
		row[3] = all_paid_jobs[i].find_all('p')[1].text  #assumption: fixed structure, so the 1st paragraph of the description is in the second <p>
		dftemp = pd.DataFrame([row], columns=('url', 'job title', 'company', 'description'))
		df = df.append(dftemp)
	
	for j in range(len(all_other_jobs)):
		row[0] = all_other_jobs[j].select('a strong')[0].parent['href']
		row[1] = all_other_jobs[j].select('a strong')[0].text
		row[2] = all_other_jobs[j].select('cite')[0].text
		row[3] = row[1] #This description is not in a tag, we will use the job title to hopefully correctly approximate the language
		dftemp = pd.DataFrame([row], columns=('url', 'job title', 'company', 'description'))
		df = df.append(dftemp)
	
	return df


def search_jobindex(title, area):         
	#title string
	#area string

	driver = webdriver.Chrome('./chromedriver')
	driver.get("https://www.jobindex.dk/?adv=1&lang=en")

	search_area = Select(driver.find_element_by_xpath('/html/body/div[1]/main/section[1]/form/div/div[1]/div[2]/select'))
	search_area.select_by_visible_text(area)

	select_posting_date = driver.find_element_by_xpath('/html/body/div[1]/main/section[1]/form/div/div[3]/div[2]/div[3]/div').click()  #click on the dropdown menu
	select_posting_date = driver.find_element_by_xpath('/html/body/div[1]/main/section[1]/form/div/div[3]/div[2]/div[3]/div/ul/li[3]/a').click() #click on '1 day'

	search_title = driver.find_element_by_name('qs')
	search_title.clear()
	search_title.send_keys(title)

	search_title.send_keys(Keys.RETURN) #pressing return on the job title search box starts the search
	page_url = driver.current_url

	try:
		driver.find_element_by_xpath('/html/body/div[1]/main/section/div[4]/div/div/div/div/button/span').click()  #weak form but close the pop up window
	except:
		pass
	driver.close()
	'''
	We could also skip the part with Selenium by noticing that the url of the search is predictible,
	build it on our own and only use BeautifulSoup
	'''
	df = pd.DataFrame(columns=('url', 'job title', 'company', 'description'))

	while True:
		try:
			df = df.append(scrap_job_data(page_url)) #Starts empty, every page's data is appended
			page = requests.get(page_url)
			soup = BeautifulSoup(page.content, 'html.parser')
			next_page_link = soup.find_all(class_='page-item page-item-next')[0].find_all('a')[0]['href']
			page_url = next_page_link
			#driver.get(page_url)
		except Exception as e:
			break
	return df


def is_in_danish(word):
	#Return True is the word or group of words is in danish, else returns False
	#word must be a string so its language can be detected
	language = detect(word)
	if language == 'da':
		return True
	else:
		return False


def findWholeWord(w):
    return re.compile(r'\b({0})\b'.format(w), flags=re.IGNORECASE).search


def is_in_taboo_list(word):
	#Returns True if the word or group of words includes a term from the taboo list, else return False
	#Word must be a string
	taboo_list = ['student', 'intern', 'HR', 'software']
	cpt = 0
	for taboo in taboo_list:
		if findWholeWord(taboo)(word) != None:
			cpt += 1

	if cpt >= 1:
		return True
	else:
		return False


def load_data_from_job_log():
	workbook = client.open("Job log") 
	sheet = workbook.worksheet("Log") 
	sheet_data = sheet.get_all_values() 
	del sheet_data[0]
	df = pd.DataFrame(sheet_data, columns=('url', 'job title', 'company')) 
	return df 


def save_to_log(df, tab = 'Log', start_cell = 'A1'):
	sheet = client.open("Job log") #open the file
	spread = Spread("Job log", config=c) #load in write mode
	spread.df_to_sheet(df, index=False, sheet= tab, start=start_cell, replace=True)    


def process_job(list_df):
	#input: list of all df from the different job searches

	df_total = pd.DataFrame(columns=('url', 'job title', 'company', 'description'))
	for df in list_df:
		df = df.reset_index(drop=True) #for some reasons the df come with a screwed up index
		df_total = df_total.append(df)
	df_total = df_total.drop_duplicates()

	for i in range(len(df_total)):
		if is_in_danish(df_total.loc[i, 'description']) == True:
			df_total = df_total.drop([i])
	df_total = df_total.reset_index(drop=True)

	for i in range(len(df_total)):
		if is_in_taboo_list(df_total.loc[i, 'job title']) == True:
			df_total = df_total.drop([i])		
	df_total = df_total.reset_index(drop=True)

	df_total = df_total.drop(columns=['description']) #The description is only useful to find the language

	df_merged = df_total.append(load_data_from_job_log(), ignore_index=True)
	len_old_data = len(load_data_from_job_log())
	df_merged = df_merged.drop_duplicates()
	save_to_log(df_merged)


def job_search():
	duo = [[''' 'data analyst' ''', 'Capital Area'], [''' 'data scientist' ''', 'Capital Area']] #list of all [job title, area]
	job_list = []
	for element in duo:
		job_list.append(search_jobindex(element[0], element[1]))   

	process_job(job_list)


