import socket
import re

config = {"server"  : "irc.freenode.net",
          "port"    : "6667",
          "nick"    : "aoeuBot",
          "channels": ["##ncss_challenge"],
          "realname": "SUBot",
          "cmd"     : "!aoeu"}

admin = ["spiritsunite"]
userTarget = ["NOTICE", "CTCP"]

sb = {}

class Message:
    def __init__(self, ircmsg):
        # Get parts
        m = re.match(r"^:([^!]+)!([^@]+)@(\S+) (\S+) (\S+) :(.+)$", ircmsg)
        if not m:
            self.good = False
            return
        self.good = True
        self.sender = m.group(1)
        self.username = m.group(2)
        self.hostname = m.group(3)
        self.command = m.group(4)
        self.target = m.group(5)
        self.message = m.group(6).strip()

    def reply(self, msg, method=None, to=None):
        if self.good:
            if not method:
                method = self.command
            if not to:
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
    ircsock.connect((config["server"], 6667))
    ircsock.send("NICK {}\n".format(config["nick"]))
    ircsock.send("USER {} 0 * :{}\n".format(config["nick"], config["realname"]))

def joinchan(chan):
    ircsock.send("JOIN {}\n".format(chan))

def handlemsg(ircmsg):
    mess = Message(ircmsg)

    if not mess.good:
        return

    # Store message in sb
    if mess.target not in sb:
        sb[mess.target] = ["<{}> {}".format(mess.sender, mess.message)]
    else:
        sb[mess.target].insert(0, "<{}> {}".format(mess.sender, mess.message))
        while len(sb[mess.target]) > 151:
            sb[mess.target].pop()
    if mess.isCmd():
        cmd(mess)
    elif config["nick"] in mess.message:
        mess.reply("What?")

def verify(nick):
    print nick
    ircsock.send("PRIVMSG NickServ :ACC {} *\n".format(nick))
    ircmsg = ""
    while "\n" not in ircmsg:
        ircmsg += ircsock.recv(1)
    m = re.match(r":.+?:(.+)", ircmsg)
    m = m.group(1).split()
    if m:
        if m[2] in admin and m[4] == "3":
            return True
    return False

def cmd(comm): 
    comm.message = comm.message[6:].strip()
    tokens = comm.message.split()
    if tokens[0] in ["quit", "restart"]:
        if verify(comm.sender):
            ircsock.send("QUIT\n")
            exit(tokens[0] == "restart")
        else:
            comm.reply("Only admins can use this command!", "NOTICE")
    elif tokens[0] in ["q", "question"]:
        tokens = comm.message.split(None, 1)
        if len(tokens) > 1 and tokens[1][-1] == "?":
            if sum(map(ord, tokens[1].rstrip("?").lower())) % 2:
                comm.reply("{}: Yes!".format(comm.sender))
            else:
                comm.reply("{}: No!".format(comm.sender))
        else:
            comm.reply("That is not a question >:C")
    elif tokens[0] in ["sb", "scrollback"]:
        if len(tokens) == 1:
            if len(sb[comm.target]) < 11:
                comm.reply(sb[comm.target][1:], "NOTICE")
            else:
                comm.reply(sb[comm.target][1:11], "NOTICE")
        else:
            try:
                line = int(tokens[1])
                comm.reply("{}".format(sb[comm.target][line]))
            except ValueError:
                comm.reply("{} is not a number!".format(tokens[1]))
            except IndexError:
                comm.reply("{} is too damn high!".format(tokens[1]))
    elif tokens[0] == "help":
        if len(tokens) == 1:
            comm.reply(["Available commands are: ", "help, q, question, quit, restart, sb, scrollback", "type \"!aoeu help <command>\" for help on the command"], "NOTICE")
        else:
            if tokens[1] == "quit":
                comm.reply("Makes the bot quit. Can only be used by admins.", "NOTICE")
            elif tokens[1] == "restart":
                comm.reply("Restarts the bot. Can only be used by admins.", "NOTICE")
            elif tokens[1] in ["q", "question"]:
                comm.reply(["USAGE: !aoeu (q/uestion) <question>", "Ask the bot a question!"], "NOTICE")
            elif tokens[1] == "help":
                comm.reply(["USAGE: !aoeu help [<command>]", "Get help on the bot's usage."], "NOTICE")
            elif tokens[1] in ["sb", "scrollback"]:
                comm.reply(["USAGE: !aoeu (sb|scrollback) [<line no>]", "Gets scrollback.", "Without any parameters, outputs last 10 lines, otherwise, outputs that line."], "NOTICE")
            else:
                comm.reply("Not a valid command", "NOTICE")
    else:
        comm.reply("Not a valid command")

if __name__ == "__main__":
    ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect()
    for chan in config["channels"]:
        joinchan(chan)

    while True:
        ircmsg = ircsock.recv(2048)
        ircmsg = ircmsg.strip("\n\r")
        print ircmsg

        # Ping? Pong
        m = re.match(r"^PING :(.+)$", ircmsg)
        if m:
            ircsock.send("PONG :{}\n".format(m.group(1)))
        else:
            handlemsg(ircmsg)
