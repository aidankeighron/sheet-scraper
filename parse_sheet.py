from googleapiclient import discovery
from googleapiclient import _auth
from get_messages import get_ids
from time import sleep
import requests
import keys

# API
credentials = _auth.credentials_from_file("trade-scraper.json")
service = discovery.build("sheets", "v4", credentials=credentials)

# Constants
MIN_CATEGORIES = 3
MIN_SHIRT_DATA = 5
MAX_EMPTY = 10
CATEGORIES = ["Name", "Number", "Size", "Type", "Year", "Description", "Availability", "Tradability", "Notes"]
RESULT = "1xDtfRs81EcdFHOiG-Nua_mBz2xAD4tFVVtNt6SjwPoM"
team_names = {}
failed_sheets = []

def get_team_number(number):
    try:
        name = team_names[str(number)]
        return name
    except:
        ...
    site = "https://www.thebluealliance.com/api/v3/team/frc"
    api = {"X-TBA-Auth-Key": keys.BLUE_ALLIANCE}
    request = requests.get(url=site+str(number), headers=api)
    team_names[str(number)] = request.json()['nickname']
    return request.json()['nickname']

def check_category(val, currentCategories):
    if val == "":
        return "none"
    val = val.lower()
    if ("name" in val and "username" not in val):
        return "Name"
    if "number" in val or ("#" in val and "team" in val):
        return "Number"
    if "size" in val:
        return "Size"
    if "type" in val or "item" in val:
        return "Type"
    if "year" in val:
        return "Year"
    if "description" in val or "info" in val or "details" in val or "decription" in val:
        return "Description"
    if "status" in val or "avail" in val:
        return "Availability"
    if "trad" in val or "rarity" in val or "likeliness" in val:
        return "Tradability"
    if "notes" in val or "other" in val or "comments" in val:
        return "Notes"
    if "team" in val: # Some sheets do this KEEP AT BOTTOM last case scenario
        return "Number"
    return "none"

def get_sheet(id):
    result = service.spreadsheets().get(spreadsheetId=id, includeGridData=True).execute()
    result = service.spreadsheets().values().get(spreadsheetId=id, range=result['sheets'][0]['properties']['title'], majorDimension="ROWS").execute()
    if "values" in result:
        return result["values"]
    else:
        return -1

def get_catagories(sheet):
    start = -1
    for tries in range(10):
        category_locations = {category:-1 for category in CATEGORIES}
        for i in range(start + 1, len(sheet)):
            for j in range(len(sheet[i])):
                if check_category(sheet[i][j], category_locations) != "none" and category_locations[check_category(sheet[i][j], category_locations)] == -1:
                    category_locations[check_category(sheet[i][j], category_locations)] = j
                    start = i
            if start == i: # Category's need to be in a row
                break
        categoryFound = sum(1 for _, category in category_locations.items() if category != -1)
        if categoryFound >= MIN_CATEGORIES:
            break
    else:
        sheet = list(zip(*sheet[::-1])) # Rotate 90 deg
        start = -1
        for tries in range(10):
            category_locations = {category:-1 for category in CATEGORIES}
            for i in range(start + 1, len(sheet)):
                for j in range(len(sheet[i])):
                    if check_category(sheet[i][j], category_locations) != "none" and category_locations[check_category(sheet[i][j], category_locations)] == -1:
                        category_locations[check_category(sheet[i][j], category_locations)] = j
                        start = i
                if start == i: # Category's need to be in a row
                    break
            categoryFound = sum(1 for _, category in category_locations.items() if category != -1)
            if categoryFound >= MIN_CATEGORIES:
                break
        else:
            raise Exception("Bad Sheet")
    end = -1
    x = -1
    y = -1
    for row in range(len(sheet)):
        for col in range(len(sheet[row])):
            val = str(sheet[row][col]).lower()
            if "wish" in val or "wants" in val or "looking" in val:
                y = row
                x = col
                break
        if y != -1:
            break
    if x != -1:
        for _, index in category_locations.items():
            if index >= x:
                end = y
    return category_locations, start, end

def parse_sheet(sheet, start, end, user, id, category_locations):
    shirts = []
    empty = 0
    for i in range(start+1, len(sheet) if end == -1 else end):
        shirt = {category:"" for category in CATEGORIES}
        shirt["User"] = user
        shirt["ID"] = id
        for category, col in category_locations.items():
            if col == -1 or col >= len(sheet[i]): # Prevent access of data outside range (happens when last index is blank)
                continue
            shirt[category] = sheet[i][col]
        shirt = list(shirt.values())
        if shirt[0] == "" and shirt[1] != "":
            try:
                int(shirt[1])
                shirt[0] = get_team_number(int(shirt[1]))
            except:
                ...
        numNotEmpty = sum(1 for col in shirt if col != '')
        if numNotEmpty >= MIN_SHIRT_DATA:
            shirts.append(shirt)
            empty = 0
        empty += 1
        if empty > MAX_EMPTY:
            break
    return shirts

def sort_sheet(shirts):
    nonInt = {}
    currentInt = 999999999
    for row in range(len(shirts)):
        try:
            shirts[row][1] = int(shirts[row][1])
        except:
            nonInt[str(currentInt)] = shirts[row][1]  
            shirts[row][1] = currentInt
            currentInt += 1          
    
    shirts.sort(key=lambda x: int(x[1]))
    
    for row in range(len(shirts)):
        try:
            if shirts[row][1] >= 999999999:
                shirts[row][1] = nonInt[str(shirts[row][1])]
        except Exception as e:
            print(str(e))
    return shirts

def write_result(sheet, id):
    CATEGORIES.append("User")
    CATEGORIES.append("ID")
    sheet.insert(0, CATEGORIES)
    values = {"majorDimension": "ROWS", "range": "Sheet1", "values": sheet}
    result = service.spreadsheets().values().update(spreadsheetId=id, range="Sheet1", valueInputOption="RAW", body=values).execute()
    format = {'requests': [
                {'updateSheetProperties': {
                    'properties': {'gridProperties': {'frozenRowCount': 1}},
                    'fields': 'gridProperties.frozenRowCount',
                }},
                {'repeatCell': {
                    'range': {'endRowIndex': 1},
                    'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
                    'fields': 'userEnteredFormat.textFormat.bold',
                }},
            ]}
    service.spreadsheets().batchUpdate(spreadsheetId=id, body=format).execute()
    return result

# Shirts
shirts = []
spreadsheet_id, users = get_ids()
user_dict = {}
for i, id in enumerate(spreadsheet_id):
    user_dict[str(id)] = users[i]
spreadsheet_id = sorted(set(spreadsheet_id))
for i, id in enumerate(spreadsheet_id):
    print(id + ": " + str(i+1) + "/" + str(len(spreadsheet_id)))
    try:
        if id == "1ojK_kAABYEeGfwMdtBxCXNZ3qh_pE9ss71W8A2v2lJE": # Bad sheet
            continue
        sheet = get_sheet(id)
        if sheet == -1:
            continue
        cat, start, end = get_catagories(sheet)
        sheet = parse_sheet(sheet, start, end, user_dict[str(id)], id, cat) # "1suhkm54lF5jBzUnV67mc_mjXAvyBNQDj8PESTOPaLko"
        for shirt in sheet:
            shirts.append(shirt)
    except Exception as e:
        print(str(e))
        print("FAILED")
        failed_sheets.append(id)
    sleep(10) # Quota
sleep(10)
existing = get_sheet(RESULT)
if existing != -1:
    del existing[0]
    for shirt in existing:
        if shirt not in shirts:
            shirts.append(shirt)
sheet = sort_sheet(shirts)
write_result(sheet, RESULT)
print(failed_sheets)

# Counting
sheet = get_sheet(RESULT)
numberOfShirts = {}
del sheet[0]
for shirt in sheet:
    if str(shirt[1]) in numberOfShirts:
        numberOfShirts[str(shirt[1])] += 1
    else:
        numberOfShirts[str(shirt[1])] = 1
sheet = []
for team, num in numberOfShirts.items():
    sheet.append([team, num])
    
values = {"majorDimension": "ROWS", "range": "Count", "values": sheet}
result = service.spreadsheets().values().update(spreadsheetId=RESULT, range="Count", valueInputOption="RAW", body=values).execute()