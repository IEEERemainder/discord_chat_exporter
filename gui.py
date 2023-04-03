import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import discord_api.discord_api as discord_api
import os

root = tk.Tk()

channelsToExportVar = tk.StringVar() 
lb = tk.Listbox(root, listvariable=channelsToExportVar, selectmode='extended')

def listboxSelectedInfo(*a):
    messagebox.showinfo(message="\n".join([curlines[i] for i in lb.curselection()]))
    
lb.bind("<Double-Button-1>", listboxSelectedInfo)
lb.pack(side='left',fill="both", expand=1)

tk.Label(root, text="Tocen").pack(side='top')

tocenVar = tk.StringVar()   
tk.Entry(root, textvariable = tocenVar, show="*").pack(side='top')

tk.Label(root, text="Manage selection").pack(side='top') 

api = None
dm=None
guilds=None
guildChannels={}

def initApi():
    global api
    if api == None:
        api = discord_api.DiscordApi(tocenVar.get(), discord_api.BasicStdoutLog())
def initDMs():
    global dm
    if dm == None:
        dm = api.get_dms()      
def initGuilds():
    global guilds
    if guilds == None:
        guilds = api.get_guilds()

underlying = [] # refactor?

def getDm():
    a = [*getDmPeople(), *getDmGroups()]
    return a
def getDmPeople():
    global dm
    initApi()
    initDMs()
    people=[x for x in dm if x["type"] == 1]
    a = []
    a.append("DM (people)")
    hyp="    "
    for p in people:
        a.append(hyp + user_readable(p["recipients"][0]))
    underlying.append("DM_PEOPLE")
    underlying.extend([int(x["id"]) for x in people])
    return a
def getDmGroups():
    global dm
    initApi()
    initDMs()
    groups = [x for x in dm if x["type"] == 3]
    a = []
    a.append("DM (groups)")
    hyp="    "
    for g in groups:
        a.append(hyp + (g["name"] if g["name"] else " ") + ";".join([user_readable(x) for x in g["recipients"]]))
    underlying.append("DM_GROUPS")
    underlying.extend([int(x["id"]) for x in groups])
    return a
    
def getGuilds():
    global guilds
    initApi()
    initGuilds()
    underlying.extend([x["id"] for x in guilds])
    return [x["name"] for x in guilds]
def getGuildChannels(g):
    global guildChannels
    initApi()
    underlying.append(str(g["id"]))
    if g["id"] in guildChannels:
        channels=guildChannels[g["id"]]
        underlying.extend([int(x["id"]) for x in channels])
        return [g["name"], *[channel_readable(c, channels) for c in channels]]
    guildChannels[g["id"]] = api.get_guild_channels(g["id"], filter_=lambda x: x["type"] in [0, 2])
    channels=guildChannels[g["id"]]
    underlying.extend([int(x["id"]) for x in channels])
    return [g["name"], *[channel_readable(c, channels) for c in channels]]

def user_readable(u):
    return u["username"] + "#" + u["discriminator"]
def channel_readable(c, channels):
    prefix = c["parent_id"] and next((x["name"]+"/" for x in channels if x["id"] == c["parent_id"]), '') or ''
    return("    " + prefix + c["name"])
   
curlines = []
   
def setLines(l):
    global curlines
    curlines = l
    channelsToExportVar.set(l)

def clearUnderlying():
    global underlying
    underlying = []

def loadDm(*a):
    clearUnderlying()
    setLines(getDm())
def loadDmPeople(*a):
    clearUnderlying()
    setLines(getDmPeople())
def loadDmGroups(*a):
    clearUnderlying()
    setLines(getDmGroups())
def loadGuilds(*a):
    clearUnderlying()
    setLines(getGuilds())
def expandGuildChannels(*a):
    clearUnderlying()
    l = []
    for c in lb.curselection():
        l.extend(getGuildChannels(guilds[c]))
    setLines(l)   
   
tk.Button(root, text="DM", command=loadDm).pack(side='top')
tk.Button(root, text="DM (only people)", command=loadDmPeople).pack(side='top')
tk.Button(root, text="DM (only groups)", command=loadDmGroups).pack(side='top')
tk.Button(root, text="Guilds", command=loadGuilds).pack(side='top')
tk.Button(root, text="Sel guilds channels", command=expandGuildChannels).pack(side='top')

tk.Label(root, text="Export").pack(side='top')

fileNameVar = tk.StringVar()   
tk.Entry(root, textvariable = fileNameVar).pack(side='top')

pythonPath = "python" # assume you have it in PATH. Change to r"C:\Python310\python.exe" or something if not

def processUnderlying():
    global underlying
    a = []
    copy = underlying[:]
    for i in range(len(copy)):
        if i not in lb.curselection():
            a.append(-1)
            continue
        u = copy[i]
        if type(u) == type(0):
            a.append(str(u))
            continue
        clearUnderlying()
        if u == "DM_PEOPLE":
            getDmPeople()
        elif u == "DM_GROUPS":
            getDmGroups()
        elif type(u) == type(''):
            getGuildChannels(next((g for g in guilds if g["id"] == u)))
        underlying = underlying[1:]
        a.append(','.join([str(x) for x in underlying]))
    underlying = copy
    return a
            
def exportBase(fmt):
    underlingProcessed = processUnderlying()
    os.system(pythonPath + " discord_chat_exporter.py " + tocenVar.get() + " " + fileNameVar.get() + " -fmt " + fmt + " -c " + ' '.join([underlingProcessed[i] for i in lb.curselection()]) + " & pause")
def exportToSqlite(*a):
    exportBase("sqlite")
def exportToJson(*a):
    exportBase("json")
def exportToDataJs(*a):
    exportBase("datajs")
def showIds(*a):
    messagebox.showinfo(message=','.join([processUnderlying()[i] for i in lb.curselection()]))
    
tk.Button(root, text="SQLite", command=exportToSqlite).pack(side='top')
tk.Button(root, text="json", command=exportToJson).pack(side='top')
tk.Button(root, text=".data.js", command=exportToDataJs).pack(side='top')
tk.Button(root, text="show ids", command=showIds).pack(side='top')

root.mainloop()
