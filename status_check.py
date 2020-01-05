#!/usr/bin/env python3

import re
import argparse
import csv

import requests
from lxml import html
import telegram

import logging

from datetime import datetime, timezone

logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s - %(message)s')
URL = 'https://egov.uscis.gov/casestatus/mycasestatus.do'
USER_AGENT = '"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"'
HEADER = {'user-agent': USER_AGENT}
XPATH_STATUS = '/html/body/div[2]/form/div/div[1]/div/div/div[2]/div[3]/h1'
XPATH_DESCRIPTION = '/html/body/div[2]/form/div/div[1]/div/div/div[2]/div[3]/p'

# 3 letters, 10 digits.
USCIS_CASE_PATTERN = re.compile("^[A-Z]{3}\d{10}$")


def check_status(number):
    payload = {'initCaseSearch': 'CHECK STATUS', 'appReceiptNum': number}

    response = requests.post(URL, headers=HEADER, data=payload)
    html_document = html.fromstring(response.content)

    status_elements = html_document.xpath(XPATH_STATUS)

    if len(status_elements) != 1:
        logging.info('Receipt number {} not found at USCIS or website down.'.format(number))
        return 'Case not found', 'Seems like USCIS does not have a case for receipt number {}'.format(number)

    status_text = status_elements[0].text_content()

    info_element = html_document.xpath(XPATH_DESCRIPTION)
    info_text = info_element[0].text_content() if len(info_element) == 1 else 'No detailed description of status'

    return status_text, info_text


def send_notifications(telegram_bot_api_token, telegram_chat_id, contents):
    bot = telegram.Bot(token=telegram_bot_api_token)

    for c in contents:
        number, status, info = c
        message = \
'''Immigration Update! USCIS case {} changed.
        
{}
      
{}'''.format(number, status, info)
        logging.info(message)

        max_length = telegram.constants.MAX_MESSAGE_LENGTH - 3
        message = (message[:max_length] + '..') if len(message) > max_length else message

        bot.send_message(telegram_chat_id, message)


def check_receipt_number(number):
    return USCIS_CASE_PATTERN.match(number)


def parse_arguments():
    parser = argparse.ArgumentParser(description='USCIS Case Checker and Telegram Notifier')
    parser.add_argument('-r', '--receipts',
                        required=True, nargs='+', type=str, help='List of USCIS Receipt Numbers')
    parser.add_argument('-f', '--file',
                        required=False, type=str, help='Cache / History File')
    parser.add_argument('-t', '--telegram',
                        required=False, nargs=2, type=str, help='Telegram Config',
                        metavar=('BOT_TOKEN', 'CHAT_ID'))
    return parser.parse_args()


def read_cases_cache_file(filename):
    cases = {}
    try:
        with open(filename) as csv_file:
            reader = csv.reader(csv_file)
            # Read top down. Last status (bottom) represents current status value.
            for row in reader:
                # Valid List needs Receipt Number in row[1] and current status in row[2]
                if len(row) < 2 or not check_receipt_number(row[1]):
                    logging.warning('Invalid row in file: {}'.format(row))
                    continue

                cases[row[1]] = row[2]

    except FileNotFoundError:
        logging.warning('No file {} exits (yet). Assuming empty cache.'.format(filename))

    return cases


def write_cases_cache_file(rows, filename):
    try:
        with open(filename, mode='a') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(rows)
    except Exception:
        logging.error('Error writing to file {}. History / Cache file not created or appended to.'.format(filename))


def query_receipts(receipts, cached_cases):
    updates = []

    # Cycle through cases.
    for r in receipts:
        if not check_receipt_number(r):
            logging.warning('Receipt number {} is not in the correct format (3 letters + 10 digits), skipping...'.format(r))
            continue

        status, info = check_status(r)
        status_change = status != cached_cases.get(r)

        timestamp = datetime.now(timezone.utc).astimezone()\
            .replace(microsecond=0)\
            .isoformat()

        print('{}: {}, {}'.format(r, status, info))

        updates.append([timestamp, r, status, info, status_change])

    return updates


if __name__ == '__main__':
    args = parse_arguments()
    cached_cases = {}

    # read
    if args.file is not None:
        cached_cases = read_cases_cache_file(args.file)

    # query
    updates = query_receipts(args.receipts, cached_cases)

    # notify (on changed cases)
    if args.telegram is not None:
        send_notifications(args.telegram[0], args.telegram[1], [i[1:4] for i in updates if i[4] is True])

    # write
    if args.file is not None:
        write_cases_cache_file([i[0:4] for i in updates], args.file)
