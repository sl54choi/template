__author__ = 'electopx@gmail.com'

import re
import sys
import time
import html
import socket
import argparse
import threading
import http.client
from bs4 import BeautifulSoup
from datetime import datetime
#from urllib.parse import unquote
from urllib.parse import urlparse
from urllib.request import urlopen
from urllib.request import Request
from pandas import Series, DataFrame
from urllib.error import URLError, HTTPError
import ssl


http.client.HTTPConnection._http_vsn = 10
http.client.HTTPConnection._http_vsn_str = 'HTTP/1.0'

start = time.time()
num, maxnum = 0, 0
maxthreadsnum = 15	# If the performance of your PC is low, please adjust this value to 5 or less.
maxDepth = 5
cu, du, url, prefix, path = '', '', '', '', ''
rdfList=[]
dfDict={}
timedOutList=[]
df = DataFrame(columns=('parent', 'link', 'visited', 'depth'))
userAgentString = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36"

def init():

    global maxthreadsnum, maxDepth
    global cu, du, url, prefix		# cu: current URL, du: domain URL
    parser = argparse.ArgumentParser(description="Site link checker", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-T", "--target-url", help="Target URL to test")
    parser.add_argument("-M", "--max-thread", type=int, default=15, help="Maximum number of threads\nDefault: 15")
    parser.add_argument("-d", "--max-depth", type=int, default=5, help="Maximum number of depth to crawl\nDefault: 5")
    args = parser.parse_args()

    if args.target_url:
        url = str(args.target_url)
        up = urlparse(url)
        if all([up.scheme, up.netloc]) and up.scheme.find('http')>=0:
            prefix = up.scheme + "://"
            du = up.netloc
            cu = du + up.path
        else:
            print ('[ERR] Please be sure to include "http://" or "https://" in the target URL.')
            return False
    else:
        print ('[ERR] Please input required target URL.')
        return False

    if args.max_thread:
        maxthreadsnum = int(args.max_thread)
    
    if args.max_depth:
        if (maxDepth > 0):
            maxDepth = int(args.max_depth)
        else:
            maxDepth = 1

    return True

# Deletion the last '/' of the target URL
def checkTail(tu):

    #if tu[len(tu) - 1] == '/':
    #    tu = tu[:-1]

    return tu.rstrip('/').rstrip()

def getCode(tu):

    global rdfList		# rdfList: List array for final result
    global start, num, cu
    global timedOutList		# timedOutList: List array for timeout urls
    code = ''
    req = None
    htmlPage = None
    status = False
    visited = True
    context = ssl._create_unverified_context()

    try:
        req = Request(tu)
        req.add_header('User-Agent', userAgentString)
        htmlPage = urlopen(req, context = context)
        if htmlPage.geturl().find(tu) < 0:
            code = "302"
            status = True if htmlPage.geturl().find(cu) >= 0 else False
        else:
            code = str(htmlPage.status)
            status = True
        print('\n[OK] The server could fulfill the request to\n%s' %tu)
    except HTTPError as e:
        code = str(e.code)
        print('\n[ERR] HTTP Error: The server couldn\'t fulfill the request to\n%s' %tu)
    except URLError as e:
        code = e.reason
        print('\n[ERR] URL Error: We failed to reach in\n%s\n+ %s' %(tu, code))
    except socket.timeout as e:
        code = e.errno
        print('\n[ERR] TIMEOUT Error: We failed to reach in\n%s\n+ %s' %(tu, code))
        if tu not in timedOutList:
            timedOutList.append(tu)
            visited = False
            return (status, htmlPage, visited)

    parent = dfDict[tu]['parent']
    rows = [parent, tu, code]
    rdfList.append(rows)
    counts = len(rdfList)

    end = time.time()
    cs = end - start
    cm = cs // 60
    cs = "{0:.1f}".format(cs % 60)

    if counts == 1:
        print ('+ Searching target URL: %d(min) %s(sec)' %(cm, cs))
    else:
        sv = "{0:.1f}".format((counts * 100) / num) + '%'
        print ('+ Searching %s(%d/%d, %d): %d(min) %s(sec)' %(sv, counts, num, maxnum, cm, cs))

    return (status, htmlPage, visited)

def getLink(tu, depth):

    global df	# df: data frame
    global dfDict
    global cu, maxnum, num, maxDepth	# maxnum: maximum # of data frame
    excludedfiles = '.ico.png.jpg.jpeg.gif.pdf.bmp.tif.svg.pic.rle.psd.pdd.raw.ai.eps.iff.fpx.frm.pcx.pct.pxr.sct.tga.vda.icb.vst.com.zip'

    (status, htmlPage, visited) = getCode(tu)
    dfDict[tu]['visited'] = visited
    
    if status == False:
        return False
    
    if depth + 1 > maxDepth:
        return False

    tu = checkTail(tu)
    tokens = tu.split('/')
    lasttoken = tokens[-1]

    if lasttoken.find('?') >= 0 or lasttoken.find('#') >= 0 or\
        (len(tokens) > 3 and excludedfiles.find(lasttoken[-4:]) >= 0):
        print ('+ This URL is skipped because it`s not the target of the getLink().')
        return False
    else:
        try:
            soup = BeautifulSoup(htmlPage.read().decode('utf-8', 'ignore'), 'lxml')
        except Exception as e:
            print('[ERR] %s @%s' %(str(e), tu))
            return False
        # Adding URL from <a> tag
        #print (soup)
        #for link in soup.findAll('a', attrs={'href': re.compile('^http|^/')}):
        links = soup.findAll('a', attrs={'href': re.compile('^http|^/')})
        #print (len(links), links)
        for link in links:
            #print (link)
            nl = link.get('href')	# nl: new link
            nl = checkTail(nl)
            nl.replace('//.//', '//')
            print ('!!!!!!!!!', nl)
            if nl.startswith("/"):
                if nl.find('//') < 0:
                    nl = prefix + du + nl
                else:
                    nl = prefix.replace('//', '') + nl
            cu = cu.replace('/overview/', '')
            #print (nl, cu)
            if nl.find(cu) >= 0 and nl != tu:
                #print ('!!!!!!!!!!!!!!', nl)
                tokens = nl.split('/')
                #print (tokens)
                lasttoken = tokens[-1]
                maxnum = maxnum + 1 
                if nl not in dfDict:
                    dfDict[nl]={'parent':tu, 'visited':False, 'depth':depth+1}
                    num = num + 1
                    print ('+ Adding rows(%d):\n%s'%(num, nl))
                '''
                if nl.find('github') < 0 or\
                    ((nl.find('github') > 0 and len(tokens) > 5) and\
                    (nl.find('blob/master') > 0 or nl.find('tree/master') > 0)):
                    maxnum = maxnum + 1 
                    if nl not in dfDict:
                        dfDict[nl]={'parent':tu, 'visited':False, 'depth':depth+1}
                        num = num + 1
                        #print ('+ Adding rows(%d):\n%s'%(num, nl))
                '''                                    
        return True

def runMultithread(tu):

    global maxthreadsnum, dfDict, num
    threadsnum = 0

    if len(dfDict) == 0:
        dfDict[tu]={'parent':"",'visited':False, 'depth':0}
        num += 1
        print ('First running with getLink()')

    threads = [threading.Thread(target=getLink, args=(durl, dfDict[durl]['depth'])) for durl in dfDict if dfDict[durl]['visited'] == False]

    for thread in threads:
        threadsnum = threading.active_count()
        while threadsnum > maxthreadsnum:
            time.sleep(0.5)
            threadsnum = threading.active_count()
            print ('+ Waiting 0.5 seconds to prevent threading overflow.')
        try:
            thread.start()
        except:
            print ('[ERR] Caught an exception of "thread.start()".')

    for thread in threads:
        try:
            thread.join()
        except:
            print ('[ERR] Caught an exception of "thread.join()".')

def result(tu, cm, cs):

    global df, path, num, rdfList

    # rdf: data frame for final result
    rdf = DataFrame(rdfList, columns=['parent', 'link', 'code']) 
    rdf.sort_values(by=['link', 'parent'], ascending=[True, True], inplace=True)
    rdf.index = range(len(rdf))

    count = num
    num = len(rdf)

    print ('+ updating the total number of links from %d to %d' %(count, num))
    print ('[OK] Result')

    target = tu.replace('://','_').replace('/','_')
    path = datetime.now().strftime('%Y-%m-%d_%H-%M')
    path = path + '_' + cm + '(min)' + cs + '(sec)_' + target + '.csv'
    rdf.to_csv(path, header=True, index=True)

    return len(rdf)

if __name__ == "__main__":

    if init():
        while len(dfDict) == 0 or len(rdfList)<len(dfDict):
            runMultithread(url)
        end = time.time()
        cs = end - start
        cm = str(int(cs // 60))
        cs = "{0:.1f}".format(cs % 60)
        dnum = result(url, cm, cs)
        print ('\n[OK] The total number of links is %d.' %maxnum)
        print ('[OK] Mission complete: The number of links excluding duplication is %d.' %dnum)
        print ('[OK] The total running time is %s(min) %s(sec).' %(cm, cs))
        print ('[OK] Please check the result file. (./%s)' %path)
    else:
        print ('[ERR] Initialization faliure')
