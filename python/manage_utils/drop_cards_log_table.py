import os, sys, datetime, requests, pickle, json
import xml.etree.ElementTree as ET
python = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(python)

from domino.core import log
from domino.cli  import print_comment, Console, print_header, print_warning
from domino.databases import Databases, table_exists, drop_table
from domino.account import find_account
from discount.core import CARDS, drop_cards_log_table

if __name__ == "__main__":
    console = Console(__file__)
    print()
    print('DROP_CARDS_LOG_TABLE')
    print()
    account_id = console.input('Учетная запись')
    account = find_account(account_id)
    if account is None:
        console.error(f'Нет такой учетной записи')
        
    drop_cards_log_table(account.id, lambda msg : print(msg))
