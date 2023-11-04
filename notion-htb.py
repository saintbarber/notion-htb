import requests
from dotenv import load_dotenv
import os, sys, time
import argparse
load_dotenv()

### Argument definition

parser = argparse.ArgumentParser(description='Notion HTB integration script',formatter_class=argparse.RawDescriptionHelpFormatter)

# parser.add_argument('-d','--database-id',                      help='Database ID - Takes higher priority then value in .env file')
# parser.add_argument('-p','--page-id',                          help='Page ID - Takes higher priority then value in .env file')
parser.add_argument('-a','--active',      action='store_true', help='Get only active machines')
parser.add_argument('-r','--retired',     action='store_true', help='Get only retired machines')
parser.add_argument('-s','--scheduled',   action='store_true', help='Get scheduled for release machines')
parser.add_argument('-u','--update',      action='store_true', help='Update notion database to reflect any HTB changes')
parser.add_argument('-t','--todo',        action='store_true', help='Get only todo boxes from HTB')
parser.add_argument('-v', '--verbose',    action='store_true', help='Enable verbose mode')

parser.epilog = f"""
Example usages:
  python3 {sys.argv[0]} -sar                # Get everything
  python3 {sys.argv[0]} --update --active   # Update only active machines
"""

args = parser.parse_args()

### Env vars and auth
NOTION_API_URL_PAGES = os.getenv("NOTION_API_URL_PAGES")
NOTION_API_URL_DATABASES = os.getenv("NOTION_API_URL_DATABASES")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
HTB_TOKEN = os.getenv("HTB_TOKEN")
HTB_URL = os.getenv("HTB_URL")
PAGE_ID    = os.getenv("PAGE_ID")
DATABASE_ID    = os.getenv("DATABASE_ID")

notion_auth = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"  
}

htb_auth = {
    "User-Agent":"saintbarber", # HTB needs a fucking different user agent then python requests
    "Authorization": f"Bearer {HTB_TOKEN}",
}

# Get tags for box id
def get_tags(id):
    url = f"{HTB_URL}/api/v4/machine/tags/{id}"
    r = requests.get(url, headers=htb_auth)

    if "Unauthorized" in r.text:
        return [{"name":"Unauthorized", "color":"red"}]
    else:
        tags = r.json()['info']        
        tags = list(map(lambda tag: {"name": tag["name"]}, tags))
        return tags

def insert_box(box, count, total, status):

    # Fetch box tags
    tags = get_tags(box['id'])

    box_row = {
    "parent": {"database_id": DATABASE_ID},
    "cover":{"external":{"url":f"{HTB_URL}{box['avatar']}"}}, # https://www.hackthebox.com/storage/avatars/ID.png
    "properties": {
        "ID": {"number": box['id']},
        "Box": {"title": [{"text": {"content": box['name']}}]},
        "OS": {"select": {"name":box['os']}}, # Windows, Linux
        "Points": {"number": box['points'] if 'points' in box else 0}, # 50
        "Release Date": {"date": {"start":box['release']}}, # 2020-12-08T12:00:00Z
        "Difficulty": {"select": {"name":box['difficultyText'] if 'difficultyText' in box else box['difficulty_text'] }}, # Easy, Medium, Hard, Insane
        "Difficulty Rate": {"number": box['difficulty']}, # 77
        "User Owns": {"number": box['user_owns_count'] if 'user_owns_count' in box else 0}, # 1337
        "Root Owns": {"number": box['root_owns_count'] if 'root_owns_count' in box else 0}, # 1337
        "Rating": {"number": box['stars'] if 'stars' in box else 0}, # 4.5
        "IP": {"rich_text": [{"type":"text","text":{"content":box['ip'] if 'ip' in box else "0.0.0.0"}}]}, # 10.10.11.230
        "User": {"status": {"name":"pwned" if 'authUserInUserOwns' in box and box['authUserInUserOwns'] else "Nope" }}, # Nope, pwned
        "Root": {"status": {"name":"pwned" if 'authUserInRootOwns' in box and box['authUserInRootOwns'] else "Nope" }}, # Nope, pwned
        "Write-up": {"status": {"name":"Not started"}}, # Not started, In progress, Complete
        "Blog": {"status": {"name":"Not started"}}, # Not started, Draft, Complete
        "Status": {"select": {"name":status}}, # Retired, Active
        "VIP": {"select": {"name":"Free" if 'free' not in box or box['free'] else "VIP"}}, # Free, VIP
        "Tags": {"multi_select": tags}, 
        "Todo?": {"checkbox": box['isTodo'] if 'root_owns_count' in box else False},
        "Retiring Box": {"rich_text": [{"type":"text","text":{"content":box['retiring']['name'] if 'retiring' in box else ""}}]}
        }
    }

    print("\rAdding machine: " + box['name'], end='', flush=True)
    print("\r\nStatus: " + str(count) + "/" + str(total), end='', flush=True)

    response = requests.post(NOTION_API_URL_PAGES, json=box_row, headers=notion_auth)

    if response.status_code != 200:
        print("\n\nFailed to insert the row. Status code:", response.status_code)
        print("Response content:\n", response.text)

# API Docs - https://documenter.getpostman.com/view/13129365/TVeqbmeq#d96880c9-216b-498f-ad6f-5cc8c0b86e45  


## Get all active machines
def get_active_machines():

    url = f"{HTB_URL}/api/v4/machine/list"
    print("Fetching all active machines... ", end='', flush=True)
    r = requests.get(url, headers=htb_auth)
    print("\rFetching all active machines... Done")
    active_machines = r.json()['info']
    
    count = 0
    total = len(active_machines)

    for active_machine in active_machines:
        count +=1
        insert_box(active_machine, count, total, "Active")
        break

## Get all retired machines
def get_retired_machines():

    url = f"{HTB_URL}/api/v4/machine/list/retired"
    print("Fetching all retired machines... ", end='', flush=True)
    r = requests.get(url, headers=htb_auth)
    print("\rFetching all retired machines... Done")
    retired_machines = r.json()['info']

    count = 0
    total = len(retired_machines)

    for retired_machine in retired_machines:
        count +=1
        insert_box(retired_machine, count, total, "Retired")
        break


## Get all scheduled for release machines (unreleased)

def get_unreleased_machines():
    url = f"{HTB_URL}/api/v4/machine/unreleased"
    print("Fetching all unreleased machines... ", end='', flush=True)
    r = requests.get(url, headers=htb_auth)
    print("\rFetching all unreleased machines... Done")
    print(r.text)
    unreleased_machines = r.json()['data']

    count = 0
    total = len(unreleased_machines)

    for unreleased_machine in unreleased_machines:
        count +=1
        insert_box(unreleased_machine, count, total, "Unreleased")
        break

def continue_prompt(prompt):
    while True:

        choices = {
            "yes" : True,
            "y" : True,
            "no": False,
            "n": False
        }
        user_input = input(prompt + ", continue? (Y/n): ").strip().lower()
        
        if not user_input: # If no value is provided, default yes
            break
        elif user_input in choices: # If value is provided check if correct value
            if not  choices[user_input]:
                print("Exiting...")
                exit() 
            else:
                break 
        else:
            print("wtf are you doing?")


if __name__ == "__main__":
    

    if(args.active):
        continue_prompt("Add all currently active machines")
        get_active_machines()
    
    if(args.scheduled):
        continue_prompt("Add all unreleased machines")
        get_unreleased_machines()
    
    if(args.retired):
        continue_prompt("Add all retired machines")
        get_retired_machines()

    

    # --update 
    # If box exists in db ask if they mean to --update it or if they want to contine (adds duplicate)


    print("\nFinished")


