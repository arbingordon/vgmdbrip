import urllib.request
import http.cookiejar
from sys import argv
from xml.sax.saxutils import unescape
import os
import json
scriptdir = "\\".join(argv[0].split("\\")[0:-1])
config = json.load(open(os.path.join(scriptdir,'config.txt'), 'r'))

vgmuserid = config["userid"]  # replace this with your user id
vgmpassword = config["password"] # replace this with your vgmpassword (from cookies)
def remove(instring, chars):
    for i in range(len(chars)):
        instring = instring.replace(chars[i],"")
    return instring
    
def substring(string, frm, to):
    start = string.find(frm) + len(frm)
    if start == frm:
        return "NULL"
    length = string[start:].find(to)
    if length == -1:
        return "NULL"
    return string[start:start+length]

def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

if(len(argv) < 2):
    print("usage: " + argv[0] + " vgmdb_album_id")
    raise SystemExit(1)
cp = urllib.request.HTTPCookieProcessor()
cj = cp.cookiejar

# see cookielib.Cookie documentation for options description
cj.set_cookie(http.cookiejar.Cookie(0, 'vgmuserid', vgmuserid,
                               '80', False, '.vgmdb.net', True, False, '/',
                               True, False, None, False, None, None, None))
cj.set_cookie(http.cookiejar.Cookie(0, 'vgmpassword', vgmpassword,
                               '80', False, '.vgmdb.net', True, False, '/',
                               True, False, None, False, None, None, None))
opener = urllib.request.build_opener(cp)
opener.addheaders.append(('User-agent', 'Mozilla/5.0 (compatible)'))
mainpage = opener.open("http://vgmdb.net/album/" + argv[1]).read().decode(encoding='utf-8', errors="replace").splitlines()
maintitle = ""
for i in range(len(mainpage)):
    if(mainpage[i].find("<h1><span class=\"albumtitle\"") != -1):
        maintitle = remove(substring(mainpage[i], "\">", "</span>"), "\"*/:<>?\|")
        #print(maintitle)
        break

fldr = "Scans (VGMdb)"
for i in range(len(mainpage)):
    if(mainpage[i].find(">Covers") != -1):
        i += 8
        while(mainpage[i].find("/db/") != -1):
            ID = substring(mainpage[i], "cover=", "\"")
            title = unescape(substring(mainpage[i], ID + "\">", "</a>"))
            image = opener.open("http://vgmdb.net/db/covers-full.php?id=" + ID).read()
            ensure_dir(fldr + os.sep)
            handle = open(fldr + os.sep + remove(title, "\"*/:<>?\|") + ".jpg", "wb")
            handle.write(image)
            handle.close()
            print("FOUND cover on line " + str(i+1) + " : ID " + ID + " : title " + title + " -> SAVED!")
            i += 1
