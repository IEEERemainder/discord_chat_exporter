import discord_api.discord_api as discord_api
import json
import sys
import datetime
import re
import time
import parse_args
import os

def showTargets(targets, estimate = False):
    for channelId in targets:
        d = estimate and api.get_channel_message_count_json(channelId, supressErrors = True)
        t = api.query(api.baseUrl + f"/channels/{channelId}")
        print('guild_id' in t and t['guildId'] or 'DM', channelId, 'message' in d and d['message'] or d['total_count'])

def download(targets):
    if args.format == 'auto':
        if any((1 for x in ['sqlite3', 'db'] if args.path.endswith(x))):
            args.format = 'sqlite3'
        elif args.path.endswith('.data.js'):
            args.format = 'datajs'
        elif args.path.endswith('.json'):
            args.format = 'json'
        else:
            raise Exception('Can\'t derive format from path. Check it or use --format [sqlite3|datajs|json]')
    supported_formats[args.format](targets)    

def printProgress(currentChannelIndex, channelsCount, currentChannelId, downloadedCount, totalCount):
    print(f'[{currentChannelIndex} / {channelsCount} {currentChannelId}] {downloadedCount} / {totalCount} ({round(downloadedCount / totalCount * 100 if totalCount != 0 else 0, DIGITS_AFTER_DECIMAL_POINT)} %)', end='\r')

def common_logic(targets, fn, projector=discord_api.nop, onChannelFinished=discord_api.nop, args2=[]):
    currentChannelIndex = 0
    channelsCount = len(targets)
    processedChannels = []
    for channelId in targets:
        if channelId in processedChannels:
            print(f'skiping {channelId} as it has been already processed')
            continue
        processedChannels.append(channelId)

        totalCountJSON = api.get_channel_message_count_json(channelId, supressErrors = True)
        
        if 'message' in totalCountJSON:
            print(f'error while exporing {channelId}: {totalCountJSON["message"]}')
            continue

        totalCount = totalCountJSON['total_results']
        downloadedCount = 0
        #printProgress(currentChannelIndex, channelsCount, channelId, downloadedCount, totalCount) # don't wait until first chunc will be fetched
        # made progressFn inside get_messages_by_chunks
        def progressFn(i, result, lastSnowflake):
            printProgress(currentChannelIndex, channelsCount, channelId, downloadedCount + len(result), totalCount)

        for msg_chunk in api.get_messages_by_chunks(
                channelId,
                projector=projector, 
                lastSnowflake=args.afterSnowflake ,
                firstSnowflake=args.beforeSnowflake != -1 and args.beforeSnowflake + (1 << 22) - 1 or -1, # low 22 bits are empty so what message with same timestamp will not be downloaded
                filter_= args.messageFilter,
                progressFn = progressFn
            ):
            fn(targets, msg_chunk, channelId, *args2)
            downloadedCount += len(msg_chunk)
        currentChannelIndex += 1
        onChannelFinished(*args2)
        print() # reset \r       
        
def parse_datetime(v): 
    return v and int(datetime.datetime.fromisoformat(v).timestamp()) or -1

def sqliteCommitChannel(cursor):
    cursor.connection.commit() # don't lost huge channels. Change if exporting too many small channels

def processSQLite3(targets):
    import sqlite3
    db = sqlite3.connect(args.path)
    cur = db.cursor()
    ''' for q in [
        'CREATE TABLE IF NOT EXISTS messages (id INT PRIMARY KEY, kind INT, channelId INT, authorId INT, ts DATETIME, editedts DATETIME, callendedts DATETIME, pinned INT, content TEXT, refmsgid INT)',
        'CREATE TABLE IF NOT EXISTS users (id INT PRIMARY KEY, bot INT, discriminator INT, name TEXT, avatarUrl TEXT)',
        'CREATE TABLE IF NOT EXISTS attachments (id INT PRIMARY KEY, url TEXT, filename TEXT, size INT)',
        'CREATE TABLE IF NOT EXISTS reactions (msgid INT, emoji TEXT, count INT)',
        'CREATE TABLE IF NOT EXISTS msgsattachments (msgid INT, attid INT)',
        'CREATE TABLE IF NOT EXISTS channels (id INT PRIMARY KEY, kind INT, cat TEXT, name TEXT, pos INT, topic TEXT)'
    ]:
        cur.execute()'''
    # huh so many entities...
    cur.execute('CREATE TABLE IF NOT EXISTS messages (id INT PRIMARY KEY, authorId INT, channeld INT, content TEXT, ts DATETIME, edited DATETIME, attachments TEXT, reactions TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS users (id INT PRIMARY KEY, name TEXT, discriminator INT, bot INT, avatarUrl TEXT)')

    def sqliteFn(targets, msg_chunc, channelId, cursor):
        cursor.executemany('INSERT OR IGNORE INTO messages VALUES (?,?,?,?,?,?,?,?)', [[m['id'], m['author']['id'], m['channel_id'], m['content'], parse_datetime(m['timestamp']), parse_datetime(m['edited_timestamp']), '\t'.join([a['url'] for a in m['attachments']]), '\t'.join([r['emoji']['name'] + ':' + str(r['count']) for r in (m['reactions'] if 'reactions' in m else [])])] for m in msg_chunc])
        cursor.executemany('INSERT OR IGNORE INTO users VALUES (?,?,?,?,?)', [[m['author']['id'], m['author']['username'], m['author']['discriminator'], 1 if 'bot' in m['author'] else 0, m['author']['avatar']] for m in msg_chunc])
        #cursor.connection.commit() # don't lost any progress?
        # TODO: scip already exist messages, SELECT MAX(id) FROM messages WHERE channelId = :chId, lastSnowflace = :result

    common_logic(targets, sqliteFn, onChannelFinished=sqliteCommitChannel, args2=[cur])


def jsonfn(targets, msg_chunc, channelId, file):
    part = json.dumps(msg_chunc, ensure_ascii = False)
    file.write(part[1 : -1])
    if channelId != targets[-1]['id']:
        file.write(',')

def processJson(targets):
    with open(args.path, 'w', encoding = 'utf-8') as f:
        f.write('[')
        common_logic(targets, jsonfn, args2 = [f])  
        f.write(']')
def processDataJs(targets):
    with open(args.path, 'w', encoding='utf-8') as f:
        f.write('DATA = [')
        common_logic(targets, jsonfn, api.BasicStringifiers.message, args2 = [f]) 
        f.write('];')

def getTimestampInSFromStr(date, utc=False):
    fn = datetime.datetime.utctimetuple if utc else datetime.datetime.timetuple
    return int(time.mktime(fn(date)))

def dateStrToSnowflake(x): # https://discord.com/developers/docs/reference#snowflakes
    seconds = getTimestampInS(datetime.datetime.fromisoformat(x))
    discordEpochInS = 1420052400 # getTimestampInS('2015-01-01', True)
    return (seconds - discordEpochInS) * 1000 << 22 # increment, worker and process ids are 0, + (1 << 22) - 1 for before id

def parseChannel(x): # channelId | channelName | guildName/channelId ?
    if re.match('^\d+$', x):
        return int(x)
    initApi()
    x = x.strip()
    #raise Error('Parse channel from name is not implemented yet')
    # TODO: implement multiple layers comparation weakening? 
    if '/' in x:
        parts = x.rsplit('/',1)
        guild = next((g for g in api.get('GUILDS') if g['name'].strip() == x))
        return next((c['id'] for c in api.get('GUILD_CHANNELS', id=guild['id'])))

    for dmChannel in api.get('DM'):
        if dmChannel['name'].strip() == x:
            return dmChannel['id']
    for guild in api.get('GUILDS'):
        channels = api.get('GUILD_CHANNELS', id = guild['id'])
        if 'message' in channels:
            continue
        for channel in channels:
            if channel['name'].strip() == x:
                return channel['id']
    raise Error('Not found. That method is experimental for non-int values that are simple ids')

def parseGuild(x):
    if re.match('^\d+$', x):
        return int(x)
    initApi()
    x = x.strip()
    for guild in api.get('GUILDS'):
        if guild['name'].strip == x:
            return guild['id']

def processTargets(targets):
    for mode in modes:
        if mode in args.modes: # keep order
            modes[mode](targets)
def parseUser(x):
    if re.match('^\d+$', x):
        return int(x)
    raise Error('User search by username or nicname is not yet implemented')

supported_formats = { # rename?
    'sqlite3' : processSQLite3,
    'datajs' : processDataJs,
    'json' : processJson
}

modes = {
    'showCandidates' : lambda targets: showTargets(targets, False), 
    'showMessagesEstimate' : lambda targets: showTargets(targets, True),
    'download' : download
}

attachmentTypes = ['link', 'embed', 'file', 'video', 'image', 'sound', 'sticker']

DIGITS_AFTER_DECIMAL_POINT = 2 # change if exporting too many messages and need more precision? 

formatToExt = {
    'json' : 'json',
    'datajs' : 'data.js',
    'sqlite' : 'db'
}

class BasicRLRNotifier:
    def __init__(self):
        self.lastUrl = ''

    def notify(self, api, url, seconds):
        print()
        print('waiting', seconds, 's for url', url)
        print()
        self.lastUrl = url
        api.maxQueriesPerSecond = api.queriesPerCurrentSecond - 1

    def tryRestoreState(self, api, url):
        commonPrefix = os.path.commonprefix([self.lastUrl, url])
        if len(commonPrefix) > len(api.baseUrl):
            api.maxQueriesPerSecond = api.DISCORD_MAX_QUERIES_PER_SECOND

def initApi():
    global api
    if api == None:
        api = discord_api.DiscordApi(sys.argv[1], rateLimitReachedNotifier=BasicRLRNotifier())

api = None

if __name__ == '__main__':
    targets = []
    args = parse_args.parse_args()
    initApi()

    if args.downloadAllDm or args.downloadWholeAccount: 
        targets.extend(api.get('DM'))
    if not (args.downloadWholeAccount or args.downloadAllDm):
        if args.downloadDmTwosome:
            targets.extend(api.get('DM_TWOSOME'))
        if args.downloadDmGroups:
            targets.extend(api.get('DM_GROUPS'))
    if args.downloadWholeAccount:
        for guild in api.get('GUILDS'):
            targets.extend(api.get('GUILD_CHANNELS', id = guild['id']))
    if not args.downloadWholeAccount:
        targets.extend(args.channels)
        for guild in args.guilds:
            channels = api.get('GUILD_CHANNELS', id = guild['id'])
            if 'message' in channels:
                continue
            targets.extend(channels)
    if args.smartSelectConf:
        for guild in api.get('GUILDS'):
            if re.match(args.smartSelectConf[0], guild['name']):
                channels = api.get('GUILD_CHANNELS', id = guild['id'])
                if 'message' in channels:
                    continue
                targets.extend([ch for ch in channels if re.match(args.smartSelectConf[1], ch['name'])])
        if re.match(args.smartSelectConf[0], args.smartSelectDmName):
            targets.extend([ch for ch in api.get('DM') if re.match(re.match(args.smartSelectConf[1], dmChannel['name']))])

    if args.smartSelectCode: # in what format? lambda ch: 
        fn = eval(args.smartSelectCode)
        for guild in api.get('GUILDS'):
            channels = api.get('GUILD_CHANNELS', id = guild['id'])
            if 'message' in channels:
                continue
                targets.extend([ch for ch in channels if fn(ch)])
    g = globals()
    l = locals()
    if args.smartFilterLibs: # use at your own risk
        for p in smartFilterLibs:
            with open(p, encoding = 'utf-8') as f:
                exec(f.read(), g, l)
    if args.smartFilterCode:
        args.messageFilter = eval(args.smartFilterCode, g, l)
    if args.filterFrom:
        if args.smartFilterCode:
            filter_ = args.messageFilter
            args.messageFilter = lambda x: filter_(x) and x['author']['id'] == args.filterFrom
        else:
            args.messageFilter = lambda x: x['author']['id'] == args.filterFrom
    if 'messageFilter' not in args.__dict__:
        args.messageFilter = discord_api.nop

    # todo: implement search        

    processTargets(targets)

def validate_filename(filename):
    return re.sub(r'[^\w\d\-_\. ]+', '_', filename)

    
