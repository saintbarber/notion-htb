# notion-htb
A simple script to update notion page with HTB challeneges, labs, etc.


### Create Integration

Goto: https://www.notion.so/my-integrations

Click add new integration
Fill out basic info

Go to secrets tab and copy secret

![Alt text](images/image.png)

Update `.env` variable `NOTION_API_KEY` with the secret from previous screen.


### Copy Database Tempalte

Copy my template that uses the notion-htb.py 

https://saintbarber.notion.site/2f7f79b7c53449ac9562464bc6f1a33b?v=73040b75523647a2bcc83b11694e4fb3&pvs=4

Click duplicate

Once you have placed the database within notion locate the database ID in the URL:

[Show datbase ID in URL]

Update `.env` variable `DATABSE_ID` with the database ID from the URL.

Now give access to the integration you created with the database

TODO: [Show HTB Tables integration beging added as connection]


### Get HTB Token

Go to profile in HTB, then profile settings

Click "Create App Token", give it a name and then copy

TODO: [Show a screenshot of copying token from HTB]

Update `.env` variable `HTB_TOKEN` with the token.


### Examples

#### Add Active boxes

Using the `notion-htb.py` script you can enable the `-a` flag to insert all the currently active boxes

```
python3 notion-htb.py -a
```

The script can also add retired and/or unreleased boxes

(Adding only active and unreleased boxes)
```
python3 notion-htb.py -sa
```

#### Update notion database

Using the `--update` flag allows you to update all boxes within your notion database to reflected any changes from HTB.

```
python3 notion-htb.py -sa --update
```

## Todo

- Auto increment pagination when fetching all retired boxes
- Implement option to add speicif box either using the box id or name
- Add screenshots to readme
