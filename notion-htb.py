import requests
from dotenv import load_dotenv
import os, sys, time
import argparse
load_dotenv()

### Argument definition

parser = argparse.ArgumentParser(description='Notion HTB integration script',formatter_class=argparse.RawDescriptionHelpFormatter)

parser.add_argument('-a','--active',      action='store_true', help='Add active machines')
parser.add_argument('-r','--retired',     action='store_true', help='Add retired machines')
parser.add_argument('-s','--scheduled',   action='store_true', help='Add scheduled for release machines')
parser.add_argument('-u','--update',      action='store_true', help='Update notion database to reflect any HTB changes')
# parser.add_argument('-t','--todo',      action='store_true', help='Get only todo boxes from HTB') 
parser.add_argument('-b','--box', help='Add specific box, use either ID or Box name') # TODO: Implement this
parser.add_argument('-v', '--verbose',    action='store_true', help='Enable verbose mode')

parser.epilog = f"""
Example usages:
  python3 {sys.argv[0]} -sar                # Add everything
  python3 {sys.argv[0]} --update --active   # Add active machines and then update notion database
"""

args = parser.parse_args()

### Env vars and auth
NOTION_API_URL_PAGES = os.getenv("NOTION_API_URL_PAGES")
NOTION_API_URL_DATABASES = os.getenv("NOTION_API_URL_DATABASES")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
HTB_TOKEN = os.getenv("HTB_TOKEN")
HTB_URL = os.getenv("HTB_URL")
DATABASE_ID    = os.getenv("DATABASE_ID")

notion_auth = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"  
}


# HTB likes to rate limit after 30 requests
# Rate limit reset is 55 after first request
# This could be optimized to find roughly how many seconds are left 
# But 55 seconds isnt that bad 
def rate_limit_check(res):
    if int(res.headers['X-Ratelimit-Remaining']) < 3:
        print("\n\nWating for HTB to stop crying... :)")
        time.sleep(55)



# HTB needs a fucking different user agent then python requests 
htb_auth = {
    "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/420.69 Safari/1337.69", 
    "Authorization": f"Bearer {HTB_TOKEN}",
}



# Get tags for box id
def get_tags(id):
    url = f"{HTB_URL}/api/v4/machine/tags/{id}"
    r = requests.get(url, headers=htb_auth)        
    rate_limit_check(r)
    
    if "Unauthorized" in r.text:
        return [{"name":"Unauthorized", "color":"red"}]
    else:
        try:
            tags = r.json()['info']        
            tags = list(map(lambda tag: {"name": tag["name"]}, tags))
            return tags
        except:
            print(f"\n\nError occured: Could not get tags for box {id}")
            print(r.status_code)
            print(r.text)
            exit()

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
        "IP": {"rich_text": [{"type":"text","text":{"content":box['ip'] if 'ip' in box and box['ip'] is not None else "0.0.0.0"}}]}, # 10.10.11.230
        "User": {"status": {"name":"pwned" if 'authUserInUserOwns' in box and box['authUserInUserOwns'] else "Nope" }}, # Nope, pwned
        "Root": {"status": {"name":"pwned" if 'authUserInRootOwns' in box and box['authUserInRootOwns'] else "Nope" }}, # Nope, pwned
        "Write-up": {"status": {"name":"Not started"}}, # Not started, In progress, Complete
        "Blog": {"status": {"name":"Not started"}}, # Not started, Draft, Complete
        "Status": {"select": {"name":status}}, # Retired, Active, Unreleased
        "VIP": {"select": {"name":"Free" if 'free' not in box or box['free'] else "VIP"}}, # Free, VIP
        "Tags": {"multi_select": tags}, 
        "Todo?": {"checkbox": box['isTodo'] if 'isTodo' in box else False},
        "Retiring Box": {"rich_text": [{"type":"text","text":{"content":box['retiring']['name'] if 'retiring' in box else ""}}]}
        }
    }

    print("\rAdding machine: " + box['name'], end='', flush=True)
    print("\r\nStatus: " + str(count) + "/" + str(total), end='', flush=True)

    r = requests.post(NOTION_API_URL_PAGES, json=box_row, headers=notion_auth)
    if r.status_code != 200:
        print("\n\nError occured: Could not add box to notion database")
        print(r.status_code)
        print(r.text)
        exit()

# API Docs - https://documenter.getpostman.com/view/13129365/TVeqbmeq#d96880c9-216b-498f-ad6f-5cc8c0b86e45  

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



def get_htb_machines(type):

    if type == "Active":
        url = f"{HTB_URL}/api/v4/machine/paginated"
    elif type == "Unreleased":
        url = f"{HTB_URL}/api/v4/machine/unreleased"
    elif type == "Retired":
        url = f"{HTB_URL}/api/v4/machine/list/retired/paginated" # Will only bring 15 per page - TODO: Fix pls
    else:
        print("whats going on: " + type)
        exit()

    print(f"Fetching all {type.lower()} machines... ", end='', flush=True)
    r = requests.get(url, headers=htb_auth)
    rate_limit_check(r)
    if r.status_code != 200:
        print(f"\n\nError occured: Could not fetch {type.lower()} machines")
        print(r.status_code)
        print(r.text)
        exit()
    htb_boxes = r.json()['data']
    
    print(f"\rFetching all {type.lower()} machines... Done")

    return htb_boxes
    
def get_htb_machine(id): 
    url = f"{HTB_URL}/api/v4/machine/profile/{id}" # Can also use /profile/{box_name}
    r = requests.get(url, headers=htb_auth)
    rate_limit_check(r)
    if r.status_code != 200:
        print(f"\n\nError occured: Could not get htb machine {id}")
        print(r.status_code)
        print(r.text)
        exit()

    htb_box = r.json()['info'] # Uses info here

    return htb_box

def update_notion_boxes(notion_id_sets, total, count):

    unreleased_boxes = get_htb_machines("Unreleased")

    for page_id,htb_id in notion_id_sets:
        count += 1
            
        box = get_htb_machine(htb_id)
    
        ## Fetch all unreleased machines 
        # Check if the box is in the unreleased machines
        # If it is, then Status -> Unreleased
        #   Also set retiring machine and retiring machine retire date
        # Else it is not in unreleased then either Active or Retired: 
        # If machine has retired: 0 -> Active  (active is always 1 so no help there)
        # If machine has retired: 1 -> Retired    
        
        retiring_box = "" # Set as empty in case current box is not unreleased box
        unreleased_box = next((unreleased_box for unreleased_box in unreleased_boxes if unreleased_box['id'] == box['id']), None)
        
        
        if unreleased_box:
            print(f"\n{box['name']} is unreleased box - Updating Retiring date of {unreleased_box['retiring']['name']}")
            status = "Unreleased"
            retiring_box = unreleased_box['retiring']['name']

            # Find page id of box with id unreleased_box['retiring']['id'] and update Retiring date field with unreleased_box['release']
            page_id_retiring = [notion_id_set[0] for notion_id_set in notion_id_sets if unreleased_box['retiring']['id'] in notion_id_set]
            page_id_retiring = page_id_retiring[0] # Above returns array =/

            retiring_data = { 
                "properties": {
                    # "Release Date": {"date": {"end" : unreleased_box['release']}}, # we could also do this if we set the start as well
                    "Retiring Date": {"date": {"start":unreleased_box['release']}}
                }
            }

            r = requests.patch(f"{NOTION_API_URL_PAGES}/{page_id_retiring}",json=retiring_data, headers=notion_auth)
            if r.status_code != 200:
                print("\n\nError occured: Could not update notion datbase retiring date")
                print(r.status_code)
                print(r.text)
                exit()

        else:
            status = "Retired" if box['retired'] else "Active"
        
        tags = get_tags(box['id'])
        # print("Updating: " + box['name'])
        

        data = { 
            "properties": {
                "Points": {"number": box['points']}, # 50
                "Release Date": {"date": {"start":box['release']}}, # 2020-12-08T12:00:00Z
                "Difficulty": {"select": {"name":box['difficultyText']}}, # Easy, Medium, Hard, Insane
                "Difficulty Rate": {"number": box['difficulty']}, # 77
                "User Owns": {"number": box['user_owns_count']}, # 1337
                "Root Owns": {"number": box['root_owns_count']}, # 1337
                "Rating": {"number": box['stars']}, # 4.5
                "User": {"status": {"name":"pwned" if box['authUserInUserOwns'] else "Nope" }}, # Nope, pwned
                "Root": {"status": {"name":"pwned" if box['authUserInRootOwns'] else "Nope" }}, # Nope, pwned
                "Status": {"select": {"name":status}}, # Retired, Active, Unreleased
                "VIP": {"select": {"name":"Free" if box['free'] else "VIP"}}, # Free, VIP
                "Tags": {"multi_select": tags},
                # "Todo?": {"checkbox": box['isTodo']}, # Sorry isTodo is only shown when fetching all machines (either Retired, Active).. Meaning i cant update this section using the API that fetches 1 machine 
                "Retiring Box": {"rich_text": [{"type":"text","text":{"content":retiring_box}}]}
            }
        }

        print("\rUpdating: " + box['name'], end='', flush=True)
        print("\r\nStatus: " + str(count) + "/" + str(total), end='', flush=True)

        r = requests.patch(f"{NOTION_API_URL_PAGES}/{page_id}",json=data, headers=notion_auth) # Update page property with page_id
        
        if r.status_code != 200:
            print("\n\nError occured: Could not update notion database box")
            print(r.status_code)
            print(r.text)
            exit()


def get_notion_machines():

    print(f"Fetching all current boxes in notion")

    r = requests.post(f"{NOTION_API_URL_DATABASES}/{DATABASE_ID}/query", headers=notion_auth)
    if r.status_code != 200:
            print("\n\nError occured: Could not fetch current machines in notion datbase")
            print(r.status_code)
            print(r.text)
            exit()
    notion_boxes = r.json()['results']

    return notion_boxes


def filter_duplicates(notion_boxes, htb_boxes, type):

    notion_box_ids = [notion_box['properties']['ID']['number'] for notion_box in notion_boxes]

    print("Filtering out existing boxes...")
    new_boxes = [htb_box for htb_box in htb_boxes if htb_box["id"] not in notion_box_ids]

    total = len(new_boxes)

    return new_boxes, total


def add_boxes(boxes, total, type):
    
    count = 0
    
    for box in boxes:
        count +=1
        insert_box(box, count, total, type)



if __name__ == "__main__":

    notion_boxes = get_notion_machines()
    
    if(args.active):

        continue_prompt("Add all currently active machines")

        htb_boxes = get_htb_machines("Active")
        boxes, total = filter_duplicates(notion_boxes, htb_boxes, "Active")

        if total == 0: 
            print(f"\nNo new active machines to add")
        else: 
            add_boxes(boxes, total, 'Active')
            print()

    
    if(args.scheduled):
        continue_prompt("Add all unreleased machines")

        htb_boxes = get_htb_machines("Unreleased")
        boxes, total = filter_duplicates(notion_boxes, htb_boxes, "Unreleased")

        if total == 0: 
            print(f"\nNo new unreleased machines to add")
        else: 
            add_boxes(boxes, total, 'Unreleased')
            print()

    
    if(args.retired):
        continue_prompt("Add all retired machines")

        htb_boxes = get_htb_machines("Retired")
        boxes, total =filter_duplicates(notion_boxes, htb_boxes, "Retired")

        if total == 0: 
            print(f"\nNo new retired machines to add")
        else: 
            add_boxes(boxes, total, 'Retired')
            print()

    if(args.update):
        print("Updating all current notion boxes with HTB database")

        notion_id_sets = [(notion_box['id'],notion_box['properties']['ID']['number']) for notion_box in notion_boxes]
        total = len(notion_id_sets)
        print(f"Found {total} rows")

        update_notion_boxes(notion_id_sets, total, 0)

    
    # if(args.update):
    #     print("Updating...")

    #     if(args.active):
    #         # Update active machines
    #         update_active_machines()
    # --update 
    # If box exists in db ask if they mean to --update it or if they want to continue (adds duplicate)

    ## Update flag only gets current machines in DB and checks for changes with HTB
    ## e.g. User owns, Root owns, machine rating, machine in todo - Unreleased machines -> Active, Active machine -> retired

    # Create update property method, that will get called with the property to update and the value

    print("\nFinished")


# NO dont prompt if they want to --update, of course they dont want duplicates
# -a fetches all active machines from HTB, if they have the box already, then skip said box - same with unrelased and retired
# update command will only look at boxes already in DB and reflect possible changes from HTB