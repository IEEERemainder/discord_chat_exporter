import discord_api
import json
import sys
import datetime
import re

print("DiscordChatExporter.py v1.0, DVG, 2023. Contact Interlocked#6505 in case of trouble")

if len(sys.argv) != 5:
    print(f"Excepted 5 args, got {sys.argc}")
    exit()

tocen = sys.argv[1]

if l := len(tocen) != 70:
    print(f"Tocen should be of length 70, got {l}. If tocen format is changed comment/edit this chec")
    exit()

format = sys.argv[2]

ext = {"json":"json","datajs":"data.js","sqlite":"db"}
if format not in ext:
    print("Uncnown format {format}. Available are {', '.join(ext)}")
    exit()

def validate_filename(filename):
    return re.sub(r'[^\w\d\-_\. ]+', "_", filename)
    
fileName = validate_filename(sys.argv[3])
fileName = fileName + "." + ext[format] 
channelIds = sys.argv[4].split(',')

channelIds2 = [] # list(set(v)) changes order, is it important?
invalid = []
digitsSet=set("0123456789")
for id in channelIds:
    if set(id) - digitsSet:
        invalid.append(id)
        continue
    if id not in channelIds2:
        channelIds2.append(id)

if invalid:
    print("Invalid ids:", ','.join(invalid))

if not channelIds2:
    print("No ids to export")
    exit()
    
print("Chosen format:", format)
print("Output filename:", fileName)
print("Exporting channels:", ','.join(channelIds2))

api = discord_api.DiscordApi(tocen)

def common_logic(fn, projector=discord_api.pf, onChannelFinished=discord_api.pf, args=[]):
    i = 0
    channelsCount = len(channelIds2)
    for channelId in channelIds2:
        total = api.get_message_count_json(channelId)
        count = 0
        if "message" in total:
            print(total["message"], channelId)
            continue
        total = total["total_results"]
        print("[", channelId, i, "/", channelsCount, "]", count,"/",total, f"({round(count / total * 100, 3)} %)", end="\r") # don't wait until first chunc will be fetched
        for msg_chunc in api.get_messages_by_chuncs(channelId,projector=projector):
            fn(msg_chunc, channelId, *args)
            count += len(msg_chunc)
            print("[", channelId, i, "/", channelsCount, "]", count,"/",total, f"({round(count / total * 100, 3)} %)", end="\r")
        onChannelFinished(*args)
    print()

def jsonfn(msg_chunc, channelId, file):
    part = json.dumps(msg_chunc, ensure_ascii=False)
    file.write(part[1:-1])
    if channelId != channelIds2[-1]:
        file.write(",")         
        
def parse_datetime(v): 
    return v and int(datetime.datetime.fromisoformat(v).timestamp()) or -1

def sqliteFn(msg_chunc, channelId, cursor):
    cursor.executemany("INSERT OR IGNORE INTO messages VALUES (?,?,?,?,?,?,?,?)", [[m["id"], m["author"]["id"], m["channel_id"], m["content"], parse_datetime(m["timestamp"]), parse_datetime(m["edited_timestamp"]), "\t".join([a['url'] for a in m["attachments"]]), "\t".join([r["emoji"]["name"] + ":" + str(r["count"]) for r in (m["reactions"] if "reactions" in m else [])])] for m in msg_chunc])
    cursor.executemany("INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)", [[m["author"]["id"], m["author"]["username"], m["author"]["discriminator"], 1 if "bot" in m["author"] else 0, m["author"]["avatar"]] for m in msg_chunc])
    #cursor.connection.commit() # don't lost any progress?
    # TODO: scip already exist messages, SELECT MAX(id) FROM messages WHERE channelId = :chId, lastSnowflace = :result

def sqliteCommitChannel(cursor):
    cursor.connection.commit() # don't lost huge channels. Change if exporting too many small channels

if format == "json":
    with open(fileName, "w", encoding="utf-8") as f:
        f.write("[")
        common_logic(jsonfn, args=[f])  
        f.write("]")
elif format == "datajs":
    with open(fileName, "w", encoding="utf-8") as f:
        f.write("DATA = [")
        common_logic(jsonfn, api.basic_readable_message, [f]) 
        f.write("];")
elif format == "sqlite":
    import sqlite3
    db = sqlite3.connect(fileName)
    cur = db.cursor()
    """cur.execute("CREATE TABLE IF NOT EXISTS messages (id INT PRIMARY KEY, kind INT, channelId INT, authorId INT, ts DATETIME, editedts DATETIME, callendedts DATETIME, pinned INT, content TEXT, refmsgid INT)");
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INT PRIMARY KEY, bot INT, discriminator INT, name TEXT, avatarUrl TEXT)");
    cur.execute("CREATE TABLE IF NOT EXISTS attachments (id INT PRIMARY KEY, url TEXT, filename TEXT, size INT)");
    cur.execute("CREATE TABLE IF NOT EXISTS reactions (msgid INT, emoji TEXT, count INT)");
    cur.execute("CREATE TABLE IF NOT EXISTS msgsattachments (msgid INT, attid INT)");
    cur.execute("CREATE TABLE IF NOT EXISTS channels (id INT PRIMARY KEY, kind INT, cat TEXT, name TEXT, pos INT, topic TEXT)");"""
    # huh so many entities...
    cur.execute("CREATE TABLE IF NOT EXISTS messages (id INT PRIMARY KEY, authorId INT, channeld INT, content TEXT, ts DATETIME, edited DATETIME, attachments TEXT, reactions TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INT PRIMARY KEY, name TEXT, discriminator INT, bot INT, avatarUrl TEXT)")
    common_logic(sqliteFn, onChannelFinished=sqliteCommitChannel, args=[cur])