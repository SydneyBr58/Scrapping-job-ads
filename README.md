# Scrapping-job-ads

Job portals are a great tools to check new job ads. However the results returned can be inaccurate and searches for job titles in a similar field usually yield many duplicates.

The purpose of this script is to perform searches for defined job titles and locations on Jobindex.dk, scrap the result to collect the job title, company and the url of the job ad. The results are filtered to remove duplicates, ads in danish and it filters out some defined key words. The output is then written on a Google spreadsheet and updated every time the code is run.

This code will need to be modified to include your own list of job titles, locations and key words to be filtered out. 
It is suggested to run the code once a day as it collects ads uploaded the day before, instead of all ads currently online.
