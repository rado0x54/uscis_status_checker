# USCIS Case Checker

Yet another USCIS Case Checker. My requirement was that i wanted to be able 
to create one or more history files in csv (per case or one for multiple cases)
and only be notified via telegram if the current status changes.

Furthermore I wanted the individual script execution to be handled by `cron`.

### Usage:

```bash
usage: status_check.py [-h] -r RECEIPTS [RECEIPTS ...] [-f FILE]
                       [-t BOT_TOKEN CHAT_ID]

USCIS Case Checker and Telegram Notifier

optional arguments:
  -h, --help            show this help message and exit
  -r RECEIPTS [RECEIPTS ...], --receipts RECEIPTS [RECEIPTS ...]
                        List of USCIS Receipt Numbers
  -f FILE, --file FILE  Cache / History File
  -t BOT_TOKEN CHAT_ID, --telegram BOT_TOKEN CHAT_ID
                        Telegram Config
```

Please do not spam USCIS by using that script and only query in moderate time frames.
