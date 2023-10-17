#!/usr/bin/env python3

import os, shutil, unicodedata, re, tempfile, requests
from pprint import pprint
from rocketchat_API.rocketchat import RocketChat
from datetime import datetime

# Function to generate filename slug
def slugify(value, allow_unicode=False):
    value = str(value)
    value = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")

# Save attachments into the assets folder
def saveAtt(assDir, attachment, msg):
    rfile = instanceURL + attachment['title_link']
    lfile = assDir + "/" + attachment['title']
    headers = {
        'X-User-Id': userID,
        'X-Auth-Token': authToken,
        'Content-Type': 'application/json'
    }
    r = requests.get(rfile, headers=headers, allow_redirects=True)
    open(lfile, 'wb').write(r.content)

# Translate action codes to name
def actionAlias(msg):
    match msg['t']:
        case 'uj':
            alias = 'joined the channel'
            return alias
        case 'ul':
            alias = 'left this channel'
            return alias
        case 'ult':
            alias = 'left this team'
            return alias
        case 'user-added-room-to-team':
            alias = 'added '+ msg['msg'] + ' to this team'
            return alias
        case 'user-converted-to-team':
            alias = 'converted '+ msg['msg'] + ' to a team'
            return alias
        case 'user-converted-to-channel':
            alias = 'converted '+ msg['msg'] + ' to a channel'
            return alias
        case 'user-deleted-room-from-team':
            alias = 'deleted '+ msg['msg'] + ' room'
            return alias
        case 'user-removed-room-from-team':
            alias = 'removed '+ msg['msg'] + ' from the team'
            return alias
        case 'ujt':
            alias = 'joined the team'
            return alias
        case 'au':
            alias = 'added ' + msg['msg'] + ' to room'
            return alias
        case 'added-user-to-team':
            alias = 'added ' + msg['msg'] + ' to this team'
            return alias
        case 'r':
            alias = 'changed room name to ' + msg['msg']
            return alias
        case 'ru':
            alias = 'removed '+ msg['msg']
            return alias
        case 'removed-user-from-team':
            alias = 'removed '+ msg['msg'] + ' from the team'
            return alias
        case 'wm':
            alias = 'welcomed ' +msg['msg']
            return alias
        case 'livechat-close':
            alias = 'Conversation finished'
            return alias
        case 'livechat-started':
            alias = 'Chat started'
            return alias
        case 'room-archived':
            alias = 'archived room'
            return alias
        case 'room-unarchived':
            alias = 'unarchived room'
            return alias
        case 'subscription-role-added':
            alias = 'set ' + msg['msg'] + " as " + msg['role']
            return alias
        case 'subscription-role-removed':
            alias = 'removed ' + msg['msg'] + " as " + msg['role']
            return alias
        case _:
            alias = msg['t']
            return alias

# Export message info as html file
def exportMessage(msg, alias, attachment, user):
    userHtml = "<strong>"+user+"</strong>"
    dateHtml = " (" + msg['ts'] + ") <br/>\n"
    msgHtml = msg['msg'].encode().decode('unicode_escape') + '</p>'
    if alias != None:
        msgHtml = "<i>"+alias+"</i>"
    if attachment != None:
        msgHtml = '<a href="./assets/' + attachment['title'] + '">' + attachment['title'] + "</a>"
        if 'description' in attachment:
            msgHtml += '</br>' + attachment['description']
    mEnt = '<p>' + userHtml + dateHtml + msgHtml + '\n' + '</p>\n'
    return mEnt

userID = 'userid'
authToken = 'token'

outputDir = './'
instanceURL = 'https://myinstance'
rocket = RocketChat(user_id=userID, auth_token=authToken, server_url=instanceURL)
allGroups = rocket.groups_list_all(count='0').json()['groups']

for x in range(len(allGroups)):
    if 'archived' in allGroups[x]:
        if allGroups[x]['archived'] == True:

            # Generate folder structure and tmp dir
            tD = tempfile.TemporaryDirectory()
            projDir = tD.name
            assDir = projDir + '/assets'
            os.mkdir(assDir)
            gID = allGroups[x]['_id']
            gName = allGroups[x]['name']
            chanFile = projDir + '/' + gName + '.html' 

            # Take ownership of room
            rocket.groups_unarchive(gID)
            rocket.groups_invite(gID, userID) # Need "Add User to Any Private Channel" permission
            rocket.groups_add_owner(gID, user_id=userID)
            gInfo = rocket.groups_info(room_name=gName).json()['group']

            f = open(chanFile, "w")
            f.write('<meta http-equiv="content-type" content="text/html; charset=utf-8">\n')
            f.write('<html>\n<body>')
            gHist=rocket.groups_history(gID, count=0).json()['messages']

            # Loop through messages in room and parse each
            for i in range(len(gHist)):
                alias = None
                attachment = None
                user = None
                msg = gHist[i]
                if 'u' in msg:
                    user = msg['u']['username'] 
                if 't' in msg:
                    alias = actionAlias(msg)
                elif 'attachments' in msg:
                    for x in range(len(msg['attachments'])):
                        attachment = msg['attachments'][x]
                        saveAtt(assDir, attachment, msg)
                f.write(exportMessage(msg, alias, attachment, user))

            f.write('</body>')
            f.close()

            zipDir = projDir + "/."
            filename = outputDir + slugify(datetime.today().strftime('%Y-%m-%d_%H-%M-')+gName+"_"+str("rc-export"))
            shutil.make_archive(filename, 'zip', zipDir)

            tD.cleanup()
