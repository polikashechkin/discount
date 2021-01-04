import os, sys
from domino.core import log
from domino.account import Account

ACCOUNT_ID = '00679015'
INVOIC = 'INVOIC'
INVOICIN = 'INVOICIN'
INVRPT = 'INVRPT'
ICR = 'ICR'
CHAIN_CODE = '929000181'

class Settings:
    def __init__(self):
        self.account = Account(ACCOUNT_ID)

    @property
    def def_address(self):
        return self.account.get_product_param('e_loreal', 'def_address')
    @def_address.setter
    def def_address(self, value):
        self.account.set_product_param('e_loreal','def_address', value)

    @property
    def def_city(self):
        return self.account.get_product_param('e_loreal', 'def_city')
    @def_city.setter
    def def_city(self, value):
        self.account.set_product_param('e_loreal','def_city', value)

    @property
    def def_code(self):
        return self.account.get_product_param('e_loreal', 'def_code')
    @def_code.setter
    def def_code(self, value):
        self.account.set_product_param('e_loreal','def_code', value)

    @property
    def partner_code(self):
        return self.account.get_product_param('e_loreal', 'partner_code')
    @partner_code.setter
    def partner_code(self, value):
        self.account.set_product_param('e_loreal','partner_code', value)

    @property
    def partner_uid(self):
        return self.account.get_product_param('e_loreal', 'partner_uid')
    @partner_uid.setter
    def partner_uid(self, value):
        self.account.set_product_param('e_loreal','partner_uid', value)

    @property
    def store_uid(self):
        return self.account.get_product_param('e_loreal', 'store_uid')
    @store_uid.setter
    def store_uid(self, value):
        self.account.set_product_param('e_loreal','store_uid', value)

    @property
    def ftp_server(self):
        return self.account.get_product_param('e_loreal', 'ftp_server')
    @ftp_server.setter
    def ftp_server(self, value):
        self.account.set_product_param('e_loreal', 'ftp_server', value)

    @property
    def ftp_user(self):
        return self.account.get_product_param('e_loreal','ftp_user')
    @ftp_user.setter
    def ftp_user(self, value):
        self.account.set_product_param('e_loreal','ftp_user', value)

    @property
    def ftp_passwd(self):
        return self.account.get_product_param('e_loreal','ftp_passwd')
    @ftp_passwd.setter
    def ftp_passwd(self, value):
        self.account.set_product_param('e_loreal','ftp_passwd', value)

    @property
    def ftp_uri(self):
        return f'{self.ftp_user}:{self.ftp_passwd}@{self.ftp_server}'

    @property
    def ftp_folder(self):
        return f'//SELLOUT/{self.partner_code}'
