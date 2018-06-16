__author__ = 'electopx@gmail.com'

import re
import sys
import time
import pandas as pd
from bs4 import BeautifulSoup
from enchant import DictWithPWL
from urllib.request import urlopen
from urllib.request import Request
from pandas import Series, DataFrame
from enchant.checker import SpellChecker
from urllib.error import URLError, HTTPError

inputname, outputname, logname = 'input.csv', 'output.csv', 'output.log'
# The most common file types and file extensions
excludedfiles = '.aif.cda.mid.mp3.mpa.ogg.wav.wma.wpl.7z.arj.deb.pkg.rar.rpm.tar.z.zip.bin.dmg.iso.toa.vcd.csv.dat.db.log.mdb.sav.sql.tar.xml.apk.bat.bin.cgi.com.exe.gad.jar.py.wsf.fnt.fon.otf.ttf.ai.bmp.gif.ico.jpe.png.ps.psd.svg.tif.asp.cer.cfm.cgi.js.jsp.par.php.py.rss.key.odp.pps.ppt.ppt.c.cla.cpp.cs.h.jav.sh.swi.vb.ods.xlr.xls.xls.bak.cab.cfg.cpl.cur.dll.dmp.drv.icn.ico.ini.lnk.msi.sys.tmp.3g2.3gp.avi.flv.h26.m4v.mkv.mov.mp4.mpg.rm.swf.vob.wmv.doc.odt.pdf.rtf.tex.txt.wks.wpd'
#useragent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36"
useragent = 'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36'

def cleanhtml(text):

    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, ' ', text)

    return cleantext

def unescape(text):

    text = text.replace('&amp;', '&').replace('&quot;', '"').replace('&apos;', "'").replace('&lt;', '<').replace('&gt;', '>')

    return text

def getCode(tu):

    global useragent
    code, targetpage = '', ''
    status = False

    try:
        req = Request(tu)
        req.add_header('User-Agent', useragent)
        targetpage = urlopen(req)
        code = str(targetpage.status)
        print('\n[OK] The server could fulfill the request to\n%s' %tu)
        status = True
    except HTTPError as e:
        code = str(e.code)
        print('\n[ERR] HTTP Error: The server couldn\'t fulfill the request to\n%s\n+ Error Code: %s' %(tu, code))
    except URLError as e:
        code = e.reason
        print('\n[ERR] URL Error: We failed to reach in\n%s\n+ Error Code: %s' %(tu, code))

    return (status, targetpage)

def init():

    global inputname, outputname, logname
    args = sys.argv[0:]
    optionLen = len(args)

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

    if inputname.find('.csv') < 0:
        print ('[ERR] Please use ".csv" as the extension of input file')
        return False
    elif outputname.find('.csv') < 0:
        print ('[ERR] Please use ".csv" as the extension of output file.')
        return False
    elif logname.find('.log') < 0:
        print ('[ERR] Please use ".log" as the extension of log file.')
        return False

    return True

if __name__ == '__main__':

    count = 0
    text, output = '', ''
    chkr = SpellChecker("en_US")
    result = DataFrame(columns=('misspelling', 'duplication', 'wiki', 'wikiurl', 'url', 'sentence' ))
    excludedwords = 'www,href,http,https,html,br'

    if init():
        f = open(logname, 'w')
        df = pd.read_csv(inputname)
        print (df.to_string())
        for link in df['link']:
            tokens = link.split('/')
            lasttoken = tokens[len(tokens) - 1]
            if link.find('?') >= 0 or lasttoken.find('#') >= 0 or lasttoken.find('%') >= 0 or excludedfiles.find(lasttoken[-4:]) >= 0:
                continue
            (status, page) = getCode(link)
            if status == False:
                continue
            #page = urlopen(link)
            soup = BeautifulSoup(page, 'lxml')
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
                        rows = [str(err.word), -1, -1, '', link, text]
                        result.loc[len(result)] = rows
        f.write(output)
        f.close()
        # Counting for duplicated misspellings
        for rowdata in result.values:
            if rowdata[1] == -1:	# rowdata[1]: duplication
                duplicatedcount = len(result.loc[result['misspelling'] == rowdata[0]])
                result.loc[result['misspelling'] == rowdata[0], 'duplication'] = duplicatedcount
            else:
                continue
        # Getting values from Wikipedia
        print ('\n + Finding words misspelled on Wikipedia')
        for rowdata in result.values:
            time.sleep(0.2)
            if rowdata[1] < 3 and rowdata[2] == -1:	# rowdata[2]: wiki 
                tu = 'https://en.wikipedia.org/w/index.php?search=' + rowdata[0]
                req = Request(tu)
                req.add_header('User-Agent', useragent)
                targetpage = urlopen(req)
                soup = BeautifulSoup(targetpage, 'lxml')
                if len(soup.findAll('a', attrs={'href': re.compile('/wiki/Wikipedia:Articles_for_creation')})) > 0:
                    result.loc[result['misspelling'] == rowdata[0], 'wiki'] = False
                    #result.loc[result['misspelling'] == rowdata[0], 'wikiurl'] = browser.current_url
                    result.loc[result['misspelling'] == rowdata[0], 'wikiurl'] = targetpage.geturl()
                    print ('[ERR] %s: Not found' %(rowdata[0]))
                    print (' + Link: %s' %targetpage.geturl())
                else:
                    result.loc[result['misspelling'] == rowdata[0], 'wiki'] = True
                    #result.loc[result['misspelling'] == rowdata[0], 'wikiurl'] = browser.current_url
                    result.loc[result['misspelling'] == rowdata[0], 'wikiurl'] = targetpage.geturl()
                    print ('[OK] %s: Found' %(rowdata[0]))
                    print (' + Link: %s' %targetpage.geturl())
        # Sorting result values
        result.sort_values(by=['duplication', 'wiki', 'misspelling', 'url'], ascending=[True, True, True, True], inplace=True)
        result.index = range(len(result))
        # Exporting to csv file
        result.to_csv(outputname, header=True, index=True)
        print (result.to_string())

    else:
        print ('[ERR] Initialization faliure')
