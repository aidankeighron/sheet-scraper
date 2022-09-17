import requests
import json
import keys

def retrieve_messages(channelID):
    headers = {
        "authorization": keys.DISCORD_AUTH
    }
    r = requests.get(f"https://discord.com/api/v9/channels/{channelID}/messages?limit=100", headers=headers)
    jsonn = json.loads(r.text)
    return jsonn
        
def get_sheet_id(jsonn):
    ids = []
    user = []
    for value in jsonn:
        try:
            id = value["content"].split("/d/")
            id[1] = id[1].split("/edit")
            ids.append(id[1][0])
            user.append(value['author']['username'])
        except:
            ...
    return (ids, user)

def get_ids():
    return get_sheet_id(retrieve_messages(keys.CHANNEL_ID))