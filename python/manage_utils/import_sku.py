# -*- coding: utf-8 -*-
import os, sys, json
import requests
from time import sleep
from domino.jobs import Job
from domino.core import log
from domino.databases import Databases
from e_loreal.params import ACCOUNT_ID
import e_loreal.query

def arg(i):
    try:
        return sys.argv[i]
    except:
        return None

if __name__ == "__main__":
    # определяем uuid и date
    # uuid первый пааметр, но может и не быть, определяем его по размеру (32 символа)
    conn = Databases().connect(ACCOUNT_ID)
    cur = conn.cursor()
    e_loreal.query.select_products(cur)
    with open('loreal_sku.txt', 'w') as f:
        for PRODUCT, SKU, EAN, NAME in cur:
            f.write(f'{PRODUCT}\t{SKU}\t{EAN}\t{NAME}\n')
    cur.close()
    conn.close()

    