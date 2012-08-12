import socket
import re

config = {"server"  : "irc.freenode.net",
          "port"    : "6667",
          "nick"    : "aoeuBot",
          "channels": ["##ncss_challenge"],
          "realname": "SUBot",
          "cmd"     : "!aoeu",
          "admins"  : ["spiritsunite"],
          "admin_comms": ["quit", "restart"],
          "max_sb"  : 151}

userTarget = ["NOTICE", "CTCP"]

sb = {}

class Message:
    """Handles messages sent to a channel/bot

    Assumes messages are formatted like:
    <nick>!<username>@<hostname> <command> <target> :<parameters>"""
    def __init__(self, ircmsg):
        """Gets each of the parts of a message"""
        # Get parts
        m = re.match(r"^:([^!]+)!([^@]+)@(\S+) (\S+) (\S+) :(.+)$", ircmsg)
        if not m:
            self.good = False
            return
        self.good     = True
        self.sender   = m.group(1)
        self.username = m.group(2)
        self.hostname = m.group(3)
        self.command  = m.group(4)
        self.target   = m.group(5)
        self.message  = m.group(6).strip()

    def reply(self, msg, method=None, to=None):
        """Used to reply to a user/channel

        Can accept a list of messages to send all of them."""
        if self.good:
            if not method:
                method = self.command
            if not to:
                # If message sent to channel, send reply to channel
                # If message was a pm, send reply to sender
                # Some commands do not work on channels, send those to sender
                if method in userTarget:
                    to = self.sender
                elif self.target[0] == "#":
                    to = self.target
                else:
                    to = self.sender
            if isinstance(msg, str):
                ircsock.send("{} {} :{}\n".format(method, to, msg))
            elif isinstance(msg, list):
                for i in msg:
                    ircsock.send("{} {} :{}\n".format(method, to, i))

    def isCmd(self):
        if self.good:
            return self.message[:6] == "!aoeu "

def connect():
    """Sending bot information to the server"""
    ircsock.connect((config["server"], 6667))
    ircsock.send("NICK {}\n".format(config["nick"]))
    ircsock.send("USER {} 0 * :{}\n".format(config["nick"], config["realname"]))

def joinchan(chan):
    ircsock.send("JOIN {}\n".format(chan))

def ircquit():
    ircsock.send("QUIT :{}".format(config["nick"]))

def handlemsg(ircmsg):
    """Handles messages. Does different things depending on the message"""
    global command

    # Ping? Pong
    m = re.match(r"^PING :(.+)$", ircmsg)
    if m:
        ircsock.send("PONG :{}\n".format(m.group(1)))

    mess = Message(ircmsg)

    # Message not formmated as expected? Chances are, we don't need it.
    # Ping is handled earlier
    if not mess.good:
        return

    # Store message in sb
    if mess.target not in sb:
        sb[mess.target] = ["<{}> {}".format(mess.sender, mess.message)]
    else:
        sb[mess.target].insert(0, "<{}> {}".format(mess.sender, mess.message))
        while len(sb[mess.target]) > config["max_sb"]:
            sb[mess.target].pop()

    # If matches a nickserv, check
    if mess.username == "NickServ" and mess.hostname == "services."and mess.target == config["nick"]:
        # Acc
        m = re.match(r"(\w+) -> (\w+) ACC (\d)", mess.message)
        if m:
            if verify(msg = mess):
                if command in ["quit", "restart"]:
                    ircquit()
                    exit(command == "quit")
            else:
                ircsock.send("NOTIFY {} :Only admins can use this command!\n".format(m.group(1)))
            command = ''
    elif mess.isCmd():
        cmd(mess)
    elif config["nick"] in mess.message:
        mess.reply("What?")

def verify(nick=None, msg=None):
    """Sends a verify based on a nick, or checks verification from an ACC nicserv command"""
    if nick:
        ircsock.send("PRIVMSG NickServ :ACC {} *\n".format(nick))
    elif msg:
        tokens = msg.message.split()
        if tokens[2] in config["admins"] and tokens[4] == "3":
            return True
        return False

def cmd(comm):
    """Handles commands sent to bot"""
    global command

    # Removes !aoeu from beginning
    comm.message = comm.message[6:].strip()
    tokens = comm.message.split()

    method = "NOTICE"
    if tokens[-1] in ["nonotice", "public"]:
        method = None
        tokens.pop()

    # Admin commands
    if tokens[0] in config["admin_comms"]:
        command = tokens[0]
        verify(nick = comm.sender)
    # Question
    elif tokens[0] in ["q", "question"]:
        # Get second part of question
        tokens = comm.message.split(None, 1)

        if len(tokens) > 1 and tokens[1][-1] == "?":
            if sum(map(ord, tokens[1].rstrip("?").lower())) % 2:
                comm.reply("{}: Yes!".format(comm.sender))
            else:
                comm.reply("{}: No!".format(comm.sender))
        else:
            comm.reply("That is not a question >:C")
    # Scrollback
    elif tokens[0] in ["sb", "scrollback"]:
        # If no more parameters, get up to the last 10 lines
        if len(tokens) == 1:
            if len(sb[comm.target]) < 11:
                comm.reply(sb[comm.target][1:], method)
            else:
                comm.reply(sb[comm.target][1:11], method)
        else:
            params = tokens[1].split(':')
            if len(params) == 1:
                # Gets line specified
                try:
                    line = int(tokens[1])
                    comm.reply(sb[comm.target][line])
                except ValueError:
                    comm.reply("{} is not a number!".format(tokens[1]))
                except IndexError:
                    comm.reply("{} is too damn high!".format(tokens[1]))
            elif len(params) in [2, 3]:
                try:
                    for i in xrange(len(params)):
                        if params[i] == '':
                            params[i] = None
                        else:
                            params[i] = int(params[i])
                    if len(params) == 2:
                        comm.reply(sb[comm.target][params[0]:params[1]], method)
                    elif len(params) == 3:
                        comm.reply(sb[comm.target][params[0]:params[1]:params[2]], method)
                except ValueError:
                    comm.reply("One of the parameters is not a number!")
    elif tokens[0] == "help":
        if len(tokens) == 1:
            comm.reply(["Available commands are: ", "help, q, question, quit, restart, sb, scrollback", "type \"!aoeu help <command>\" for help on the command"], "NOTICE")
        else:
            if tokens[1] == "quit":
                comm.reply("Makes the bot quit. Can only be used by admins.", method)
            elif tokens[1] == "restart":
                comm.reply("Restarts the bot. Can only be used by admins.", method)
            elif tokens[1] in ["q", "question"]:
                comm.reply(["USAGE: !aoeu (q/uestion) <question>", "Ask the bot a question!"], method)
            elif tokens[1] == "help":
                comm.reply(["USAGE: !aoeu help [<command>]", "Get help on the bot's usage."], method)
            elif tokens[1] in ["sb", "scrollback"]:
                comm.reply(["USAGE: !aoeu (sb|scrollback) [<line no>]", "Gets scrollback.", "Without any parameters, outputs last 10 lines, otherwise, outputs that line."], method)
            else:
                comm.reply("Not a valid command", method)
    else:
        comm.reply("Not a valid command")

if __name__ == "__main__":
    log = ['']
    command = ''

    ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect()
    for chan in config["channels"]:
        joinchan(chan)

    while True:
        ircmsg = ircsock.recv(4096)
        print ircmsg,
        ircmsg = ircmsg.split("\r\n")
        log[0] += ircmsg[0]
        del ircmsg[0]
        log.extend(ircmsg)

        # Ping? Pong
        for msg in log[:-1]:
            handlemsg(msg)
        log = [log[-1]]
