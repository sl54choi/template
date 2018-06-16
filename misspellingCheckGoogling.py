__author__ = 'electopx@gmail.com'

import re
import sys
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from urllib.request import urlopen
from pandas import Series, DataFrame
from enchant import DictWithPWL
from enchant.checker import SpellChecker
from urllib.error import URLError, HTTPError

inputname, outputname, logname = '', '', ''
excludedfiles = '.zip.ico.png.jpg.jpeg.gif.pdf.bmp.tif.svg.pic.rle.psd.pdd.raw.ai.eps.iff.fpx.frm.pcx.pct.pxr.sct.tga.vda.icb.vst'

def cleanhtml(text):

    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, ' ', text)

    return cleantext

def unescape(text):

    text = text.replace('&amp;', '&').replace('&quot;', '"').replace('&apos;', "'").replace('&lt;', '<').replace('&gt;', '>')

    return text

def getCode(tu):

    code = ''
    status = False

    try:
        code = str(urlopen(tu).getcode())
        print('\n[OK] The server could fulfill the request to\n%s' %tu)
        status = True
    except HTTPError as e:
        code = str(e.code)
        print('\n[ERR] HTTP Error: The server couldn\'t fulfill the request to\n%s' %tu)
    except URLError as e:
        code = e.reason
        print('\n[ERR] URL ERror: We failed to reach in\n%s\n + %s' %(tu, code))

    return status

def init():

    global inputname, outputname, logname
    args = sys.argv[0:]
    optionLen = len(args)

    if len(args) <= 1:
        print ('[ERR] There is no option.')
        return False

    # e.g.: python mt.py -i input.csv -o output.csv -l misspelling.log
    for i in range(optionLen-1):
        if args[i].upper() == '-I':	# -I: input file name
            data = str(args[i+1])
            inputname = data
        elif args[i].upper() == '-O':	# -O: output file name
            data = str(args[i+1])
            outputname = data
        elif args[i].upper() == '-L':	# -L: log file name
            data = str(args[i+1])
            logname = data

    if inputname == '' and outputname == '' and logname == '':
        print ('[ERR] Please enter names for the input, output and log file.')
        return False
    elif inputname == '' or inputname.find('.csv') < 0:
        print ('[ERR] Please enter name for the input file and be sure to include ".csv" in input file name.')
        return False
    elif outputname == '' or outputname.find('.csv') < 0:
        print ('[ERR] Please enter name for the output file and be sure to include ".csv" in output file name.')
        return False
    elif logname == '' or logname.find('.log') < 0:
        print ('[ERR] Please enter name for the log file name and be sure to include ".log" in log file name.')
        return False

    return True

if __name__ == '__main__':

    count = 0
    text, output = '', ''
    chkr = SpellChecker("en_US")
    result = DataFrame(columns=('misspelling', 'dcount', 'scount', 'url', 'sentence' ))
    excludedwords = 'www,href,http,https,html,br'
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--window-size=1920x1080')
    chrome_options.add_argument('disable-gpu')
    useragent = 'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36'
    chrome_options.add_argument(useragent)

    if init():
        f = open(logname, 'w')
        df = pd.read_csv(inputname)
        print (df.to_string())
        for link in df['link']:
            status = getCode(link)
            if status == False:
                continue
            tokens = link.split('/')
            lasttoken = tokens[len(tokens) - 1]
            if lasttoken.find('#') >= 0 or lasttoken.find('?') >= 0 or lasttoken.find('%') >= 0 or excludedfiles.find(lasttoken[-4:]) >= 0:

                continue
            html = urlopen(link)
            soup = BeautifulSoup(html, 'lxml')
            output = output + '\n* ' + link
            for text in soup.findAll('p'):
                text = unescape(" ".join(cleanhtml(str(text)).split()))
                if len(text) == 0:
                    continue
                if text[0] != '"':
                    text = '"' + text
                if text[len(text) - 1] != '"':
                    text = text + '"'
                output = output + '\n + ' + text
                print ('\n + Link: %s' %link)
                print (' + Content: %s' %text)
                chkr.set_text(text)
                for err in chkr:
                    if excludedwords.find(str(err.word)) < 0:
                        count = count + 1
                        adding = '[ERR] (' + str(count) + ') ' + str(err.word)
                        print ('%s' %adding)
                        output = output + '\n' + adding
                        rows = [str(err.word), -1, -1, link, text]
                        result.loc[len(result)] = rows
        f.write(output)
        f.close()
        # Counting for duplicated misspellings
        for rowdata in result.values:
            if rowdata[1] == -1:
                duplicatedcount = len(result.loc[result['misspelling'] == rowdata[0]])
                result.loc[result['misspelling'] == rowdata[0], 'dcount'] = duplicatedcount
            else:
                continue
        # Getting values from Googling
        print ('\n[OK] Getting the number of results searched by Googling')
        for rowdata in result.values:
            if rowdata[2] == -1 and rowdata[1] < 3:
                browser = webdriver.Chrome(chrome_options=chrome_options)
                browser.implicitly_wait(3)
                browser.get('https://google.com')
                word = '"' + rowdata[0] + '" site:https://en.wikipedia.org/wiki/' + Keys.RETURN
                browser.find_element_by_id('lst-ib').send_keys(word)
                try:
                    element = browser.find_element_by_xpath('//*[@id="resultStats"]')
                    elementtokens = element.text.split(' ')
                    searchedcount = elementtokens[2][:-1]
                    result.loc[result['misspelling'] == rowdata[0], 'scount'] = float(searchedcount.replace(',', ''))
                    print (' + %s: About %s results' %(rowdata[0], searchedcount))
                    browser.quit()
                except:
                    searchedcount = '0'
                    result.loc[result['misspelling'] == rowdata[0], 'scount'] = float(searchedcount.replace(',', ''))
                    print (' + %s: %s result' %(rowdata[0], searchedcount))
                    browser.quit()
                    continue
        # Sorting result values
        result.sort_values(by=['dcount', 'scount', 'misspelling', 'url'], ascending=[True, True, True, True], inplace=True)
        result.index = range(len(result))
        # Exporting to csv file
        result.to_csv(outputname, header=True, index=True)
        print (result.to_string())

    else:
        print ('[ERR] Initialization faliure')
