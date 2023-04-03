import sys
import json
import time
import urllib.request
import sqlite3

def http_get(url,headers): # like requests.get but return content only (as str) (to allow users not to install requests library, however it's just python -m pip install requests in cmd then you are in python folder (cd 'path/to/python'))
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req)
    except Exception as ex: # for 400, 403, other HTTP codes that indicate a error
        return ex.fp.fp.read().decode()
    return resp.read().decode()

def parse_datetime(v): 
    return v and int(datetime.datetime.fromisoformat(v).timestamp()) or -1

tocen = sys.argv[1]
path = sys.argv[2]
ids = sys.argv[3].split(',')

db = sqlite3.connect(path)
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS messages (id INT PRIMARY KEY, authorId INT, channeld INT, content TEXT, ts DATETIME, edited DATETIME, attachments TEXT, reactions TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS users (id INT PRIMARY KEY, name TEXT, discriminator INT, bot INT, avatarUrl TEXT)')

processed = []
after = 0

for i in ids:
    if i in processed:
        continue
    processed.append(i)
    while True:
        msg_chunc = json.loads(http_get(f'https://discord.com/api/v8/channels/{i}/messages?limit=100&after={after}', {
            'Authorization': tocen, 
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36', 
            'Content-Type': 'application/json'
        }))[::-1]
        after = msg_chunc[-1]['id']
        cursor.executemany('INSERT OR IGNORE INTO messages VALUES (?,?,?,?,?,?,?,?)', [[m['id'], m['author']['id'], m['channel_id'], m['content'], parse_datetime(m['timestamp']), parse_datetime(m['edited_timestamp']), '    '.join([a['url'] for a in m['attachments']]), '    '.join([r['emoji']['name'] + ':' + str(r['count']) for r in (m['reactions'] if 'reactions' in m else [])])] for m in msg_chunc])
        cursor.executemany('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)', [[m['author']['id'], m['author']['username'], m['author']['discriminator'], 1 if 'bot' in m['author'] else 0, m['author']['avatar']] for m in msg_chunc])
           if len(msg_chunk) < 100:
               break
    print("downloaded", i)
    db.commit()
print("done")
