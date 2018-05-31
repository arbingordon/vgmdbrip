from sys import argv
import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup

scriptdir = "\\".join(argv[0].split("\\")[0:-1])
config = json.load(open(os.path.join(scriptdir,'config.txt'), 'r'))

session = requests.Session()
def Soup(data):
  return BeautifulSoup(data, "html.parser")

def login():
    # x = session.get('https://vgmdb.net/db/main.php')
    # s = Soup(x.content).find('input', type='hidden')['value']
    # print(s)
    # with open('debug1.html', 'wb') as f:
        # f.write(x.content)
    username = config['username']
    password = config['password']
    BASE_URL = 'https://vgmdb.net/forums/'
    x = session.post(BASE_URL + 'login.php?do=login', {
    'vb_login_username':        username,
    'vb_login_password':        password,
    'vb_login_md5password':     hashlib.md5(password.encode()).hexdigest(),
    'vb_login_md5password_utf': hashlib.md5(password.encode()).hexdigest(),
    'cookieuser': 1,
    'do': 'login',
    's': '',
    'securitytoken': 'guest'
    })
    # with open('debug2.html', 'wb') as f:
        # f.write(x.content)

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

login()
soup = ""
if(argv[1].isnumeric()):
  soup = Soup(session.get("https://vgmdb.net/album/" + argv[1]).content)
else:
  query = " ".join(argv[1:])
  soup = Soup(session.get("https://vgmdb.net/search?q=\"" + query + "\"").content)
  if(soup.title.text[:6] == "Search"):
    print("stuck at search results")
    exit(1)

print(soup.title.text)

folder = "Scans (VGMdb)"
for scan in soup.find("div", attrs={"class" : "covertab",  "id" : "cover_gallery"}).find_all("a"):
  url = scan["href"]
  image = session.get(url).content
  title = scan.text.strip() + url[-4:]
  ensure_dir(folder + os.sep)
  sanitized = remove(title, "\"*/:<>?\|")
  with open(os.path.join(folder, sanitized), "wb") as f:
      f.write(image)

  print(title + " downloaded")