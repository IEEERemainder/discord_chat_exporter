import argparse
import discord_chat_exporter

def parse_args():
    parser = argparse.ArgumentParser(
        prog = 'discord_chat_exporter.py',
        description = 'Downloads discord chats logs as from a user',
        epilog = 'DVG, 2023. Conctact Interlocked#6505 for help'
    )

    parser.add_argument(
        'token', 
        help = "User's token to access Discord API. You can obtain it by loggin in discord via browser, opening DevTools (Ctrl + Shift + I for most popular browsers), going to network tab, opening channel you haven't opened in this session (and if they has not accumulated enought messages to load it from cache) (you may reload page if unsure if understand it or want to), searching a request named like 'messages?limit=50', opening it's details, copying value of 'Authorization' field in 'Request Headers'. Granting it to either user or program may result in account lose, so beware it. This program doesn't perform any malicious actions, however, you should be able to check the code in notepad if needed"
    )
    parser.add_argument(
        'path',
        help = "Path to save the downloaded messages with filename with extension format is derived from. Format also can be defined by -fmt or --format"
    )

    parser.add_argument(
        '-fmt', '--format',
        dest = "format",
        help = "Set the format to bypass the one specified in the path",
        default='auto',
        metavar = '|'.join(discord_chat_exporter.supported_formats),
        choices = discord_chat_exporter.supported_formats.keys()
    )

    parser.add_argument(
        '-m', '--mode',
        dest = "modes",
        nargs = '+',
        action = 'extend',
        choices = discord_chat_exporter.modes.keys(),
        default = ["download"],
        metavar = ("mode=" + "|".join(discord_chat_exporter.modes), "mode"),
        help = "Thatever to start download immediately or just show that is gonna be downloaded or that costs would it take"
    )

    parser.add_argument(
        '-c', '--channel',
        dest = "channels",
        type = discord_chat_exporter.parseChannel, 
        nargs = '+',
        action = 'extend',
        metavar = 'channelId|channelName|guildName/channelName',
        default = [],
        help = "Save messages of channels with specified id(s)"
    )
    parser.add_argument(
        '-g', '--guilds',
        dest = "guilds",
        type = discord_chat_exporter.parseGuild, 
        nargs = '+',
        action = 'append',
        metavar = 'guildId|guildName',
        default = [],
        help = "Save messages of channels of guilds with specified id(s)"
    )

    parser.add_argument(
        '-s-s', '--smart-select',
        dest = "smartSelectConf",
        nargs = 2,
        action = 'append',
        metavar = ('guildPattern', 'channelPattern'),
        default = None,
        help = "Save messages of channels of guilds matches regex pattern. Use --mode showCandidates to examine founds and --smart-select-dm-name if have guild(s?) with name DIRECT_MESSAGES"
    )
    parser.add_argument(
        '-s-s-py', '--smart-select-python',
        dest = "smartSelectCode",
        metavar = 'pythonCode',
        help = "Save messages of channels of guilds those return value from python function (message : dict) -> Any piped throught bool() is True"
    )
    parser.add_argument(
        '-s-s-dm-p', '--smart-select-dm-name',
        dest = "smartSelectDmName",
        default = "DIRECT_MESSAGES",
        metavar = "name",
        help = "Set a guidName equivalent for DM since it's processed by --smart-select too",
    )
    parser.add_argument(
        '-s-flt', '--smart-filter',
        dest = "smartFilterCode",
        metavar = "pythonCode",
        help = "Filter messages by python function of signature (message : dict) -> bool. If you gonna perform multiple queries better download all messages and then query local database (if discord's own search doesn't match). Runs on every message, so consider search if looking for specific messages"
    )
    parser.add_argument(
        '-s-i', '--smart-include',
        dest = "smartFilterLibs",
        nargs = '+',
        action = 'extend',
        default=[],
        metavar = 'library.py',
        help = "Execute --smart-* dependency scripts by their paths. Probably not really secure if you have no idea that do they do [or their own dependencies]{1,}"
    )
    parser.add_argument(
        '-w', '--whole-account',
        dest = "downloadWholeAccount",
        action = 'store_true',
        help = "Set whatever to download messages of all available to account channels"
    )
    parser.add_argument(
        '-dm', '--direct-messages',
        dest = "downloadAllDm",
        action = 'store_true',
        help = "Set whatever to download messages of whole DM's channels"
    )
    parser.add_argument(
        '-dm-t', '--direct-messages-twosome-only',
        dest = "downloadDmTwosome",
        action = 'store_true',
        help = "Set whatever to download messages of 1-to-1 DM's channels"
    )
    parser.add_argument(
        '-dm-g', '--direct-messages-groups-only',
        dest = "downloadDmGroups",
        action = 'store_true',
        help = "Set whatever to download messages of group DM's channels"
    )

    parser.add_argument(
        '-a', '--after-date',
        dest = "afterSnowflake",
        type = discord_chat_exporter.dateStrToSnowflake,
        metavar = "isoDate",
        default=0,
        help = "Override begin of channels to export"
    )
    parser.add_argument(
        '-b', '--before-date',
        dest = "beforeSnowflake",
        type = discord_chat_exporter.dateStrToSnowflake,
        default=-1,
        metavar = "isoDate",
        help = "Override end of channels to export"
    )
    parser.add_argument(
        '-f', '--from',
        dest = 'filterFrom',
        type = discord_chat_exporter.parseUser,
        metavar = 'user',
        default=None,
        help = 'Fetch all messages accoring to other args but save only ones sent by defined users. Consider --search too'
    )
    parser.add_argument(
        '-s', '--search',
        dest = "searchQuery",
        metavar = "query",
        help = "Search messages matching that criteria (text search) and --search-* criterias via discord search api"
    )
    parser.add_argument(
        '-s-f', '--search-from',
        dest = "searchFrom",
        type = str,
        metavar = "user",
        help = "Filter messages by author"
    )
    parser.add_argument(
        '-s-m', '--search-mentions',
        dest = "searchMentions",
        type = str,
        nargs = '+',
        action = 'append',
        metavar="user",
        help = "Filter messages that mentions ALL specified users"
    )

    parser.add_argument(
        '-s-h', '--search-has',
        dest = "searchHas",
        type = str,
        nargs = '+',
        action = 'append',
        choices = discord_chat_exporter.attachmentTypes,
        default = [],
        metavar = ("attachmentType=" + "|".join(discord_chat_exporter.attachmentTypes), "attachmentType"),
        help = "Filter by attachments types"
    )
    parser.add_argument(
        '-s-p', '--search-pinned',
        dest = "searchPinned",
        type = int, # bool may be misleading cause -s-p 0 and no arg is different states
        choices = [0, 1],
        default = -1,
        metavar = "0|1",
        help = "Filter messages that are pinned or not"
    )
    parser.add_argument(
        '-s-c', '--search-channels',
        dest = "searchChannels",
        type = int,
        nargs = '+',
        action = 'extend',
        default = [],
        metavar="channel",
        help = "Filter messages in channels with specified ids"
    )
    parser.add_argument(
        '-s-a', '--search-after',
        dest = "searchAfter",
        type = discord_chat_exporter.dateStrToSnowflake,
        metavar = "isoDate",
        help = "Cut off messages before date"
    )
    parser.add_argument(
        '-s-b', '--search-before',
        dest = "searchBefore",
        type = discord_chat_exporter.dateStrToSnowflake,
        metavar = "isoDate",
        help = "Cut off messages after date"
    )
    parser.add_argument(
        '-s-d', '--search-during',
        dest = "searchAfter",
        type = discord_chat_exporter.dateStrToSnowflake,
        metavar = "isoDate",
        help = "Filter messages sent only in specified date YYYY-MM-DD"
    )
    
    return parser.parse_args()