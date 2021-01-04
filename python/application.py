import sys, os, json, sqlite3, arrow, importlib, datetime, pickle, time
from flask import Flask, make_response, request, render_template
#import xml.etree.cElementTree as ET
from lxml import etree as ET
              
from domino.core import log, DOMINO_ROOT
from domino.application import Application, Status
from domino.account import find_account, find_account_id
                               
from settings import log as discount_log
                                                                                  
from discount.calculator import Calculator, AccountWorker, AccountDeptWorker
from discount.action_types import ActionTypes
from discount.card_types import CardTypes
from discount.checks import Check
from discount.cards import Card
from discount.series import Series
from discount.core import DISCOUNT_DB, CARDS, Engine, MODULE_ID
from grants import Grants
from domino.databases.postgres import Postgres
from domino.databases.sqlite import Sqlite
from discount.pos import PosCheck 
       
# Зависимости
# > Используемые базы данных и таблицы
# > Используемые базы данных и таблицы
#   > Postgres # wdwdwdwdwdwddwdwd user = self.Postgres.query(User).get(100)
#      > Document # wdwdwdwdwdwdwd wdwdwd  
#      > Line # wdwdwdwdwdwdwd wdwdwd  
#      > EgaisDocument # wdwdwdwdwdwdwd wdwdwd  
#      > EgaisLine # wdwdwdwdwdwdwd wdwdwd  
#      > ExciseMark # wdwdwdwdwdwdwd wdwdwd  
       
POSTGRES = Postgres.Pool()
SQLITE = Sqlite.Pool()
                                                                                                                                                                                                                                                                         
app = Flask(__name__)
application = Application(os.path.abspath(__file__), framework='MDL')

from navbar import navbar

application['navbar'] = navbar
application['calculator'] = Calculator(application)

application['action_types'] = ActionTypes(application)
application['card_types'] = CardTypes(application)
application['card_classes'] = application['card_types']

#-------------------------------------------    
import domino.pages.version_history
@app.route('/domino/pages/version_history', methods=['POST', 'GET'])
@app.route('/domino/pages/version_history.<fn>', methods=['POST', 'GET'])
def _domino_pages_version_history(fn = None):
    return application.response(request, domino.pages.version_history.Page, fn)
  
import domino.pages.procs
@app.route('/domino/pages/procs', methods=['POST', 'GET'])
@app.route('/domino/pages/procs.<fn>', methods=['POST', 'GET'])
def _domino_pages_procs(fn = None):
    return application.response(request, domino.pages.procs.Page, fn)
  
import domino.pages.proc_shedule
@app.route('/domino/pages/proc_shedule', methods=['POST', 'GET'])
@app.route('/domino/pages/proc_shedule.<fn>', methods=['POST', 'GET'])
def _domino_pages_proc_shedule(fn = None):
    return application.response(request, domino.pages.proc_shedule.Page, fn)
       
import domino.pages.jobs
@app.route('/domino/pages/jobs', methods=['POST', 'GET'])
@app.route('/domino/pages/jobs.<fn>', methods=['POST', 'GET'])
def _domino_pages_jobs(fn = None):
    return application.response(request, domino.pages.jobs.Page, fn)
            
import domino.pages.job
@app.route('/domino/pages/job', methods=['POST', 'GET'])
@app.route('/domino/pages/job.<fn>', methods=['POST', 'GET'])
def _domino_pages_job(fn = None):
    return application.response(request, domino.pages.job.Page, fn)
                
import domino.responses.job
@app.route('/domino/job', methods=['POST', 'GET'])
@app.route('/domino/job.<fn>', methods=['POST', 'GET'])
def _domino_responses_job(fn=None):
    return application.response(request, domino.responses.job.Response, fn)
#-------------------------------------------    
      
import pages.dept_set
@app.route('/pages/dept_set', methods=['POST', 'GET'])
@app.route('/pages/dept_set.<fn>', methods=['POST', 'GET'])
def _pages_dept_set(fn=None):
    return application.response(request, pages.dept_set.Page, fn, [POSTGRES, SQLITE])
       
import pages.grants
@app.route('/pages/grants', methods=['POST', 'GET'])
@app.route('/pages/grants.<fn>', methods=['POST', 'GET'])
def _pages_grants(fn=None): 
    return application.response(request, pages.grants.Page, fn, [POSTGRES])
 
from pages.schema_grants import SchemaGrantsPage
@app.route('/pages/schema_grants', methods=['POST', 'GET'])
@app.route('/pages/schema_grants.<fn>', methods=['POST', 'GET'])
def _pages_schema_grants(fn=None) : 
    return application.response(request, SchemaGrantsPage, fn, [POSTGRES])
    
from pages.grant import GrantPage
@app.route('/pages/grant', methods=['POST', 'GET'])
def _pages_grant() : 
    return application.response(request, GrantPage, None, [POSTGRES])
@app.route('/pages/grant.<fn>', methods=['POST', 'GET'])
def _pages_grant_fn(fn):
    return application.response(request, GrantPage, fn, [POSTGRES])

import pages.reports
@app.route('/pages/reports', methods=['POST', 'GET'])
def _pages_report() : 
    return application.response(request, pages.reports.Page, None, [POSTGRES])
@app.route('/pages/reports.<fn>', methods=['POST', 'GET'])
def _pages_reports_fn(fn):
    return application.response(request, pages.reports.Page, fn, [POSTGRES])
  
import pages.start_page
@app.route('/pages/start_page', methods=['POST', 'GET'])
@app.route('/pages/start_page.<fn>', methods=['POST', 'GET'])
def _pages_start_page(fn=None) : 
    return application.response(request, pages.start_page.Page, fn, [POSTGRES])
  
import pages.card_types
@app.route('/pages/card_types', methods=['POST', 'GET'])
@app.route('/pages/card_types.<fn>', methods=['POST', 'GET'])
def _pages_card_types(fn=None): 
    return application.response(request, pages.card_types.Page, fn, [POSTGRES, SQLITE])
                             
import pages.cards
@app.route('/pages/cards', methods=['POST', 'GET'])
@app.route('/pages/cards.<fn>', methods=['POST', 'GET'])
def _pages_cards(fn=None): 
    return application.response(request, pages.cards.ThePage, fn, [POSTGRES])
                                                
import pages.card 
@app.route('/pages/card', methods=['POST', 'GET'])
@app.route('/pages/card.<fn>', methods=['POST', 'GET'])
def _pages_card(fn=None) : 
    return application.response(request, pages.card.Page, fn, [POSTGRES])

#< pages/card_classes
import pages.card_classes
@app.route('/pages/card_classes', methods=['POST', 'GET'])
def _pages_card_classes():
    try:
        page = pages.card_classes.Page(application, request)
        return page.make_response() 
    except BaseException as ex:
        log.exception(request)
        return f'{ex}', 500
@app.route('/pages/card_classes.<fn>', methods=['POST', 'GET'])
def _pages_card_classes_fn(fn):
    try:
        page = pages.card_classes.Page(application, request)
        return page.make_response(fn) 
    except BaseException as ex:
        log.exception(request)
        return f'{ex}', 500
#>       
import pages.fs_checks
@app.route('/pages/fs_checks', methods=['POST', 'GET'])
@app.route('/pages/fs_checks.<fn>', methods=['POST', 'GET'])
def _pages_fs_checks(fn=None) : 
    return application.response(request, pages.fs_checks.ThePage, fn, [POSTGRES])
                              
import pages.fs_check 
@app.route('/pages/fs_check', methods=['POST', 'GET'])
@app.route('/pages/fs_check.<fn>', methods=['POST', 'GET'])
def _pages_fs_check(fn=None): 
    return application.response(request, pages.fs_check.ThePage, fn, [POSTGRES])
                                                                                    
import pages.schemas
@app.route('/pages/schemas', methods=['POST', 'GET'])
@app.route('/pages/schemas.<fn>', methods=['POST', 'GET'])
def _pages_schemas(fn = None): 
    return application.response(request, pages.schemas.Page, fn, [POSTGRES, SQLITE])
                                               
import pages.schema 
@app.route('/pages/schema', methods=['POST', 'GET'])
@app.route('/pages/schema.<fn>', methods=['POST', 'GET'])
def _pages_schema(fn=None): 
    return application.response(request, pages.schema.ThePage, fn, [POSTGRES, SQLITE])
              
import pages.shemes
@app.route('/pages/shemes', methods=['POST', 'GET'])
@app.route('/pages/shemes.<fn>', methods=['POST', 'GET'])
def _pages_shemes(fn = None): 
    return application.response(request, pages.shemes.Page, fn, [POSTGRES, SQLITE])
               
import pages.call_center
@app.route('/pages/call_center', methods=['POST', 'GET'])
@app.route('/pages/call_center.<fn>', methods=['POST', 'GET'])
def _pages_call_center(fn=None):
    return application.response(request, pages.call_center.Page, fn, [POSTGRES])
                                           
#application.page('pages.product_sets')
import pages.product_sets
@app.route('/pages/product_sets', methods=['POST', 'GET'])
def product_sets_page() : 
    start = time.perf_counter()
    log.debug(f'product_sets_PAGE')
    response = pages.product_sets.ThePage(application, request).make_response() 
    ms = round((time.perf_counter() - start) * 1000, 3)
    log.debug(f'product_sets_PAGE {ms} MS')
    return response 
@app.route('/pages/product_sets.<fn>', methods=['POST', 'GET'])
def product_sets_page_fn(fn):
    start = time.perf_counter()
    log.debug(f'product_sets_PAGE_FN {fn}')
    response = pages.product_sets.ThePage(application, request).make_response(fn)
    ms = round((time.perf_counter() - start) * 1000, 3)
    log.debug(f'product_sets_PAGE_FN {ms} MS')
    return response  
                                                                                                                                   
from pages.product_set import ThePage as ProductSetPage
@app.route('/pages/product_set', methods=['POST', 'GET'])
@app.route('/pages/product_set.<fn>', methods=['POST', 'GET'])
def _pages_products_set(fn=None) : 
    return application.response(request, ProductSetPage, fn, [POSTGRES, SQLITE])
                       
import responses.download_product_set
@app.route('/responses/download_product_set', methods=['POST', 'GET'])
@app.route('/responses/download_product_set.<fn>', methods=['POST', 'GET'])
def _responses_download_product_set(fn=None):
    return application.response(request, responses.download_product_set.Response, fn, [SQLITE, POSTGRES])
 
import responses.report 
@app.route('/report', methods=['POST', 'GET'])
@app.route('/report.<fn>', methods=['POST', 'GET'])
def _responses_report(fn = None):
    return application.response(request, responses.report.Response, fn, [POSTGRES])

#< page /pages/product_set_query_column
import pages.product_set_query_column
@app.route('/pages/product_set_query_column', methods=['POST', 'GET'])
def _pages_product_set_query_column() : 
    try:    
        return pages.product_set_query_column.Page(application, request).make_response() 
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500
@app.route('/pages/product_set_query_column.<fn>', methods=['POST', 'GET'])
def _pages_product_set_query_column_fn(fn):
    try: 
        return pages.product_set_query_column.Page(application, request).make_response(fn)
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500
#>                  
                       
from pages.test import ThePage as TestPage
@app.route('/pages/test', methods=['POST', 'GET'])
@app.route('/pages/test.<fn>', methods=['POST', 'GET'])
def _pages_test(fn=None): 
    return application.response(request, TestPage, fn , [POSTGRES, SQLITE])
    
import pages.test_cards
@app.route('/pages/test_cards', methods=['POST', 'GET'])
@app.route('/pages/test_cards.<fn>', methods=['POST', 'GET'])
def _pages_test_card_fn(fn=None):
    return application.response(request, pages.test_cards.Page, fn, [POSTGRES]) 
 
import pages.test_goods
@app.route('/pages/test_goods', methods=['POST', 'GET'])
@app.route('/pages/test_goods.<fn>', methods=['POST', 'GET'])
def _pages_test_goods(fn=None): 
    return application.response(request, pages.test_goods.Page, fn, [POSTGRES, SQLITE]) 
  
from domino.reports import ReportsPage
@app.route('/pages/reports', methods=['POST', 'GET'])
def reports_page() : 
    start = time.perf_counter()
    log.debug(f'ReportsPage')
    try:
        response = ReportsPage(application, request).make_response() 
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500
    ms = round((time.perf_counter() - start) * 1000, 3)
    log.debug(f'ReportsPage : {ms} ms')
    return response
@app.route('/pages/reports.<fn>', methods=['POST', 'GET'])
def reports_page_fn(fn):
    start = time.perf_counter()
    log.debug(f'ReportsPage.{fn}')
    try:
        response = ReportsPage(application, request).make_response(fn)
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500
    ms = round((time.perf_counter() - start) * 1000, 3)
    log.debug(f'ReportsPage.{fn} : {ms} ms')
    return response
            
# ReportPage
from domino.reports import ReportPage
@app.route('/report', methods=['POST', 'GET'])
def report_page() : 
    start = time.perf_counter()
    log.debug(f'PageReport')
    try:
        response = ReportPage(application, request).make_response() 
    except BaseException as ex:
        ms = round((time.perf_counter() - start) * 1000, 3)
        log.debug(f'ReportPage : {ms} MS : {ex}')
        log.exception(request.url)
        return f'{ex}', 500
    ms = round((time.perf_counter() - start) * 1000, 3)
    log.debug(f'ReportPage : {ms} MS')
    return response
@app.route('/report.<fn>', methods=['POST', 'GET'])
def report_page_fn(fn):
    start = time.perf_counter()
    log.debug(f'PageReport.{fn}')
    try: 
        response = ReportPage(application, request).make_response(fn)
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500
    ms = round((time.perf_counter() - start) * 1000, 3)
    log.debug(f'ReportPage.{fn} : {ms} MS')
    return response
                                     
import pages.action_types
@app.route('/pages/action_types', methods=['POST', 'GET'])
@app.route('/pages/action_types.<fn>', methods=['POST', 'GET'])
def _pages_action_types(fn=None):
    return application.response(request, pages.action_types.Page, fn)
 
import pages.change_log
@app.route('/pages/change_log')
@app.route('/pages/change_log.<fn>')
def _pages_change_log(fn=None):
    return application.response(request, pages.change_log.Page, fn)
         
#----------------------------------------
# PROCS
# ---------------------------------------                                                                                                                                                              
#application.page('load')
from load import ThePage as LoadPage
@app.route('/load', methods=['POST', 'GET'])
def load_page():
    try:
        return LoadPage(application, request).make_response() 
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500
@app.route('/load.<fn>', methods=['POST', 'GET'])
def load_page_fn(fn):
    try:  
        return LoadPage(application, request).make_response(fn) 
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500
                        
import procs.cleaning 
@app.route('/procs/cleaning', methods=['POST', 'GET'])
@app.route('/procs/cleaning.<fn>', methods=['POST', 'GET'])
def _procs_cleaning(fn = None): 
    return application.response(request, procs.cleaning.Page, fn)
    
#application.page('remove_checks')
from remove_checks import ThePage as RemoveChecksPage
@app.route('/remove_checks', methods=['POST', 'GET'])
def remove_checks_page():
    try:
        return RemoveChecksPage(application, request).make_response() 
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500
@app.route('/remove_checks.<fn>', methods=['POST', 'GET'])
def remove_checks_page_fn(fn):
    try:
        return RemoveChecksPage(application, request).make_response(fn) 
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500
                  
#---------------------------------------- 
# EXPORT_CARDS
#---------------------------------------- 
from export_cards import ThePage as ExportCardsPage
@app.route('/export_cards', methods=['POST', 'GET'])
def export_cards_page() : 
    start = time.perf_counter()
    log.debug(f'PAGE export_cards')
    try:
        response = ExportCardsPage(application, request).make_response() 
    except BaseException as ex:
        log.exception(request.url)
        response = f'{ex}', 500
    ms = round((time.perf_counter() - start) * 1000, 3)
    log.debug(f'PAGE export_cards : {ms} MS')
    return response
@app.route('/export_cards.<fn>', methods=['POST', 'GET'])
def export_cards_fn(fn):
    start = time.perf_counter()
    log.debug(f'PAGE export_cards : {fn}')
    response = ExportCardsPage(application, request).make_response(fn)
    ms = round((time.perf_counter() - start) * 1000, 3)
    log.debug(f'PAGE export_cards : {fn} : {ms} MS')
    return response
                                             
#---------------------------------------- 
# CALC_DISCOUNT
#---------------------------------------- 
from procs.calc_discount import CalcDiscountPage
@app.route('/calc_discount', methods=['POST', 'GET'])
def calc_discount() : 
    try:
        return CalcDiscountPage(application, request).make_response() 
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500
@app.route('/calc_discount.<fn>', methods=['POST', 'GET'])
def calc_discount_fn(fn):
    try:
        return CalcDiscountPage(application, request).make_response(fn)
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500
 
#----------------------------------------
# CARD_CLASSES
# ---------------------------------------                                                                                                                                                              
from card_types.C01 import ThePage as C01Page
@app.route('/card_types/C01', methods=['POST', 'GET'])
@app.route('/card_types/C01.<fn>', methods=['POST', 'GET'])
def _card_types_C01(fn=None): 
    return application.response(request, C01Page, fn, [POSTGRES, SQLITE])
  
from card_types.C02 import ThePage as C02Page
@app.route('/card_types/C02', methods=['POST', 'GET'])
@app.route('/card_types/C02.<fn>', methods=['POST', 'GET'])
def _card_types_C02(fn=None) : 
    return application.response(request, C02Page, fn, [POSTGRES, SQLITE])
 
from card_types.C03 import ThePage as C03Page
@app.route('/card_types/C03', methods=['POST', 'GET'])
@app.route('/card_types/C03.<fn>', methods=['POST', 'GET'])
def _card_types_C03(fn=None):
    return application.response(request, C03Page, fn, [POSTGRES, SQLITE])
 
from card_types.C04 import ThePage as C04Page
@app.route('/card_types/C04', methods=['POST', 'GET'])
@app.route('/card_types/C04.<fn>', methods=['POST', 'GET'])
def _card_types_C04(fn=None) : 
    return application.response(request, C03Page, fn, [POSTGRES, SQLITE])
                                                                                                                                                              
#----------------------------------------
# ACTION_TYPES
# ---------------------------------------
import action_types.A29
@app.route('/action_types/A29', methods=['POST', 'GET'])
@app.route('/action_types/A29.<fn>', methods=['POST', 'GET'])
def _action_types_A29(fn=None): 
    return application.response(request, action_types.A29.Page, fn, [SQLITE, POSTGRES])
     
import action_types.A28
@app.route('/action_types/A28', methods=['POST', 'GET'])
@app.route('/action_types/A28.<fn>', methods=['POST', 'GET'])
def _action_types_A28(fn=None): 
    return application.response(request, action_types.A28.Page, fn, [SQLITE, POSTGRES])
                         
import action_types.A27
@app.route('/action_types/A27', methods=['POST', 'GET'])
@app.route('/action_types/A27.<fn>', methods=['POST', 'GET'])
def _action_types_A27(fn=None): 
    return application.response(request, action_types.A27.Page, fn, [SQLITE, POSTGRES])

import action_types.A26
@app.route('/action_types/A26', methods=['POST', 'GET'])
@app.route('/action_types/A26.<fn>', methods=['POST', 'GET'])
def _action_types_A26(fn=None): 
    return application.response(request, action_types.A26.Page, fn, [SQLITE, POSTGRES])
  
import action_types.A25
@app.route('/action_types/A25', methods=['POST', 'GET'])
@app.route('/action_types/A25.<fn>', methods=['POST', 'GET'])
def _action_types_A25(fn=None): 
    return application.response(request, action_types.A25.Page, fn, [SQLITE, POSTGRES])

import action_types.A24
@app.route('/action_types/A24', methods=['POST', 'GET'])
@app.route('/action_types/A24.<fn>', methods=['POST', 'GET'])
def _action_types_A24(fn=None) : 
    return application.response(request, action_types.A24.Page, fn, [SQLITE, POSTGRES])

import action_types.A22
@app.route('/action_types/A22', methods=['POST', 'GET'])
@app.route('/action_types/A22.<fn>', methods=['POST', 'GET'])
def _action_types_A22(fn=None): 
    return application.response(request, action_types.A22.Page, fn, [SQLITE, POSTGRES])

import action_types.A21
@app.route('/action_types/A21', methods=['POST', 'GET'])
@app.route('/action_types/A21.<fn>', methods=['POST', 'GET'])
def _action_types_A21(fn=None) : 
    return application.response(request, action_types.A21.Page, fn, [SQLITE, POSTGRES])

from action_types.A20 import ThePage as A20Page
@app.route('/action_types/A20', methods=['POST', 'GET'])
@app.route('/action_types/A20.<fn>', methods=['POST', 'GET'])
def _action_types_A20(fn=None) : 
    return application.response(request, A20Page, fn, [SQLITE, POSTGRES])

from action_types.A19 import ThePage as A19Page
@app.route('/action_types/A19', methods=['POST', 'GET'])
@app.route('/action_types/A19.<fn>', methods=['POST', 'GET'])
def _action_types_A19(fn=None) : 
    return application.response(request, A19Page, fn, [SQLITE, POSTGRES])
                                                                                                                                                                  
from action_types.A1 import ThePage as A1Page
@app.route('/action_types/A1', methods=['POST', 'GET'])
@app.route('/action_types/A1.<fn>', methods=['POST', 'GET'])
def _action_types_A1(fn=None): 
    return application.response(request, A1Page, fn, [SQLITE, POSTGRES])
    
from action_types.A2 import ThePage as A2Page
@app.route('/action_types/A2', methods=['POST', 'GET'])
@app.route('/action_types/A2.<fn>', methods=['POST', 'GET'])
def _action_types_A2(fn=None) : 
    return application.response(request, A2Page, fn, [SQLITE, POSTGRES])
      
from action_types.A3 import ThePage as A3Page
@app.route('/action_types/A3', methods=['POST', 'GET'])
@app.route('/action_types/A3.<fn>', methods=['POST', 'GET'])
def A3_page(fn=None) : 
    return application.response(request, A3Page, fn, [SQLITE, POSTGRES])
 
from action_types.A4 import ThePage as A4Page
@app.route('/action_types/A4', methods=['POST', 'GET'])
@app.route('/action_types/A4.<fn>', methods=['POST', 'GET'])
def A4_page(fn=None) : 
    return application.response(request, A4Page, fn, [SQLITE, POSTGRES])
 
import action_types.A4_1
@app.route('/action_types/A4_1', methods=['POST', 'GET'])
@app.route('/action_types/A4_1.<fn>', methods=['POST', 'GET'])
def _action_types_A4_1(fn=None) : 
    return application.response(request, action_types.A4_1.Page, fn, [SQLITE, POSTGRES])

from action_types.A6 import ThePage as A6Page
@app.route('/action_types/A6', methods=['POST', 'GET'])
@app.route('/action_types/A6.<fn>', methods=['POST', 'GET'])
def A6_page(fn=None): 
    return application.response(request, A6Page, fn, [SQLITE, POSTGRES])

from action_types.A7 import ThePage as A7Page
@app.route('/action_types/A7', methods=['POST', 'GET'])
@app.route('/action_types/A7.<fn>', methods=['POST', 'GET'])
def A7_page(fn=None) : 
    return application.response(request, A7Page, fn, [SQLITE, POSTGRES])

from action_types.A8 import ThePage as A8Page
@app.route('/action_types/A8', methods=['POST', 'GET'])
@app.route('/action_types/A8.<fn>', methods=['POST', 'GET'])
def A8_page(fn=None): 
    return application.response(request, A8Page, fn, [SQLITE, POSTGRES])

from action_types.A9 import ThePage as A9Page
@app.route('/action_types/A9', methods=['POST', 'GET'])
@app.route('/action_types/A9.<fn>', methods=['POST', 'GET'])
def A9_page(fn=None) : 
    return application.response(request, A9Page, fn, [SQLITE, POSTGRES])

from action_types.A10 import ThePage as A10Page
@app.route('/action_types/A10', methods=['POST', 'GET'])
@app.route('/action_types/A10.<fn>', methods=['POST', 'GET'])
def A10_page(fn=None) : 
    return application.response(request, A10Page, fn, [SQLITE, POSTGRES])
    
import action_types.A10_1
@app.route('/action_types/A10_1', methods=['POST', 'GET'])
@app.route('/action_types/A10_1.<fn>', methods=['POST', 'GET'])
def _action_types_A10_1(fn=None) : 
    return application.response(request, action_types.A10_1.Page, fn, [SQLITE, POSTGRES])
       
from action_types.A11 import ThePage as A11Page
@app.route('/action_types/A11', methods=['POST', 'GET'])
@app.route('/action_types/A11.<fn>', methods=['POST', 'GET'])
def A11_page(fn=None): 
    return application.response(request, A11Page, fn, [SQLITE, POSTGRES])
     
from action_types.A12 import ThePage as A12Page
@app.route('/action_types/A12', methods=['POST', 'GET'])
@app.route('/action_types/A12.<fn>', methods=['POST', 'GET'])
def _action_types_A12(fn=None): 
    return application.response(request, A12Page, fn, [SQLITE, POSTGRES])

from action_types.A13 import ThePage as A13Page
@app.route('/action_types/A13', methods=['POST', 'GET'])
@app.route('/action_types/A13.<fn>', methods=['POST', 'GET'])
def A13_page(fn=None): 
    return application.response(request, A13Page, fn, [SQLITE, POSTGRES])

from action_types.A14 import ThePage as A14Page
@app.route('/action_types/A14', methods=['POST', 'GET'])
@app.route('/action_types/A14.<fn>', methods=['POST', 'GET'])
def A14_page(fn=None) : 
    return application.response(request, A14Page, fn, [SQLITE, POSTGRES])

from action_types.A15 import ThePage as A15Page
@app.route('/action_types/A15', methods=['POST', 'GET'])
@app.route('/action_types/A15.<fn>', methods=['POST', 'GET'])
def A15_page(fn=None) : 
    return application.response(request, A15Page, fn, [SQLITE, POSTGRES])

from action_types.A16 import ThePage as A16Page
@app.route('/action_types/A16', methods=['POST', 'GET'])
@app.route('/action_types/A16.<fn>', methods=['POST', 'GET'])
def A16_page(fn=None) : 
    return application.response(request, A16Page, fn, [SQLITE, POSTGRES])
 
from action_types.A17 import ThePage as A17Page
@app.route('/action_types/A17', methods=['POST', 'GET'])
@app.route('/action_types/A17.<fn>', methods=['POST', 'GET'])
def A17_page(fn=None) : 
    return application.response(request, A17Page, fn, [SQLITE, POSTGRES])
                  
from action_types.A18 import ThePage as A18Page
@app.route('/action_types/A18', methods=['POST', 'GET'])
@app.route('/action_types/A18.<fn>', methods=['POST', 'GET'])
def A18_page(fn=None) : 
    return application.response(request, A18Page, fn, [SQLITE, POSTGRES])
   
import action_types.A30
@app.route('/action_types/A30', methods=['POST', 'GET'])
@app.route('/action_types/A30.<fn>', methods=['POST', 'GET'])
def _action_types_A30(fn=None) : 
    return application.response(request, action_types.A30.Page, fn, [SQLITE, POSTGRES])

import action_types.A31
@app.route('/action_types/A31', methods=['POST', 'GET'])
@app.route('/action_types/A31.<fn>', methods=['POST', 'GET'])
def _action_types_A31(fn=None) : 
    return application.response(request, action_types.A31.Page, fn, [SQLITE, POSTGRES])
                                                                                                                                                                         
# --------------------------------------- 
#   ABOUT_XML
# ---------------------------------------
@app.route('/about_xml', methods=['POST', 'GET'])
def about_xml():
    try:
        xml = ET.fromstring('<STATUS/>')
        ET.SubElement(xml, 'status').text = f'success'
        ET.SubElement(xml, 'message').text = f'Дисконтный сервер, версия {application.version}'
        return ET.tostring(xml, encoding='utf-8')
    except BaseException as ex:
        log.exception(request.url)
        response = Status.exception(f'{ex}').xml()
        return response
                                                               
import responses.get_test_checks
@app.route('/get_test_checks', methods=['POST', 'GET'])
def _responses_get_test_checks(fn=None):
    return application.response(request, responses.get_test_checks.Response, fn, [SQLITE, POSTGRES], log=True)
          
import responses.get_test_check
@app.route('/get_test_check', methods=['POST', 'GET'])
def _responses_get_test_check(fn=None):
    return application.response(request, responses.get_test_check.Response, fn, [SQLITE, POSTGRES], log=True)

import responses.discount_test
@app.route('/discount_test', methods=['POST', 'GET'])
def _responses_discount_test(fn=None):
    return application.response(request, responses.discount_test.Response, fn)
               
  
# CHECK CARD
import responses.check_card
@app.route('/check_card', methods=['POST', 'GET'])
def _responses_check_card(fn = None):
    return application.response(request, responses.check_card.Response, fn, [POSTGRES], log=True)

# GET_KEYWORDS
import responses.get_keywords
@app.route('/get_keywords', methods=['POST'])
def _responses_get_keyword():
    return application.response(request, responses.get_keywords.Response, None, [POSTGRES], log=True)

# ACCEPT 
import responses.accept
@app.route('/accept', methods=['POST', 'GET'])
def _responses_accept(fn=None):
    return application.response(request, responses.accept.Response, fn, [POSTGRES], log=True)
# DOWNLOAD_DISCOUNT_CARDS               
def append_attrib(element, name, value):
    if value is not None:
        element.attrib[name] = f'{value}'                             
                           
@app.route('/download_discount_cards', methods=['GET', 'POST'])
def download_discount_cards():  
    try:      
        r = application.request(request)
        account_id = r.account_id() 
        DISPOSITION = r.get('disposition')
        TYPE = r.get('type')  
        TYPE_NAME = r.get('type_name')  
        xcards = ET.fromstring('<cards/>')   
        xcards.attrib['type'] = TYPE
        xcards.attrib['type_name'] = f'{TYPE_NAME}'
        xcards.attrib['create'] = f'{datetime.datetime.now()}'
                
        conn = application.account_database_connect(account_id)
        cards = Card.findall(conn.cursor(), 'TYPE=:0 order by ACTIVATE_DATE', [TYPE])
        conn.close() 
               
        #for card in sorted(cards, key=lambda card : card.активация_дата, reverse=True):
        for card in cards:
            xcard = ET.SubElement(xcards, 'card')
            xcard.attrib['id'] = card.ID
            xcard.attrib['num'] = card.маркировочный_номер
            #append_attrib(xcard, 'create', card.create_date)
            append_attrib(xcard, 'activation_date', card.активация_дата)
            #append_attrib(xcard, 'check_id', card.get_attrib('check_id'))
            #append_attrib(xcard, 'check_date', card.get_attrib('check_date'))
            append_attrib(xcard, 'dept_code', card.активация_подразделение_ID)

        out  = ET.tostring(xcards, encoding='utf-8')
        response = make_response(out)
        response.headers['Content-Type'] = 'application/xml; charset=utf-8'
        #response.headers['Content-Description'] = 'File Transfer'
        if DISPOSITION is not None:
            response.headers['Content-Disposition'] = f'{DISPOSITION}'
        else:
            response.headers['Content-Disposition'] = 'attachment; filename=cards.xml'
        #response.headers['Content-Disposition'] = 'inline'
        response.headers['Content-Length'] = len(out)
        return response
    except BaseException as ex:
        log.exception(ex)
        return f'{ex}'                         

# SHOW_XML_FILE  
@app.route('/show_xml_file', methods=['GET'])
def show_xml_file():  
    try:     
        xml_file = request.args.get('xml_file')
        with open(xml_file, 'r') as f:
            response  = make_response(f.read())
        #response.headers['Content-Type'] = 'text/html; charset=utf-8'
        response.headers['Content-Type'] = 'application/xml; charset=utf-8'
        #response.headers['Content-Description'] = 'File Transfer'
        response.headers['Content-Disposition'] = 'inline'
        response.headers['Content-Length'] = os.path.getsize(xml_file)
        return response
    except BaseException as ex:
        log.exception(ex)
        return f'{ex}'                         
                  
# --------------- ------------------------
#   CALC  
# ---------------------------------------
import responses.calc
@app.route('/calc', methods=['POST', 'GET'])
def _responses_calc(fn=None):
    return application.response(request, responses.calc.Response, fn, [POSTGRES], log=True)
                  
# ---------------------------------------
#   GET_PRICES_XML 
# ---------------------------------------
import responses.get_prices_xml
@app.route('/get_prices_xml', methods=['POST', 'GET'])
def _get_prices_xml(fn=None): 
    return application.response(request, responses.get_prices_xml.Response, fn, [POSTGRES], log=True)
# ---------------------------------------
#   GET CARD
# ---------------------------------------
from discount.get_card import get_card_responce
@app.route('/get_card', methods=['POST', 'GET'])
def get_card():
    try:
        log.debug(request.url)
        return get_card_responce(application, request)
    except BaseException as ex:
        log.exception(request.url)
        return json.dumps({'status':'exception', 'message' : f'{ex}'}, ensure_ascii=False)
         
# ---------------------------------------
#   CREATE_OR_UPDATE_CARD
# ---------------------------------------
from discount.create_or_update_card import create_or_update_card_responce
@app.route('/create_or_update_card', methods=['POST', 'GET'])
def create_or_update_card():
    try:
        return create_or_update_card_responce(application, request)
    except BaseException as ex:
        log.exception(request.url)
        return json.dumps({'status':'exception', 'message' : f'{ex}'}, ensure_ascii=False)
 
# ---------------------------------------
#   GET_ACTION_NAMES
# ---------------------------------------
from discount.actions import Action
@app.route('/get_action_names', methods=['POST', 'GET'])
def get_action_names():
    names = {}
    try:
        account_id = request.args.get('account_id')
        conn = sqlite3.connect(DISCOUNT_DB(account_id))
        cur = conn.cursor()
        action_types = application['action_types']
        for action in Action.findall(cur):
            names[action.ID] = action.полное_наименование(action_types)
        return json.dumps(names, ensure_ascii=False)
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500

# ---------------------------------------
#   GET_CARD_TYPES
# ---------------------------------------
from discount.series import CardType
@app.route('/get_card_types', methods=['POST', 'GET'])
def get_card_types():
    card_types = {}
    try:
        account_id = request.args.get('account_id')
        conn = sqlite3.connect(DISCOUNT_DB(account_id))
        cur = conn.cursor()
        for card_type in CardType.findall(cur):
            card_type_id = card_type.id
            info = {}
            info['name'] = card_type.полное_наименование
            info['class'] = card_type.type
            card_types[card_type_id] = info
        return json.dumps(card_types, ensure_ascii=False)
    except BaseException as ex:
        log.exception(request.url)
        return f'{ex}', 500
                  
import pages.protocol 
@app.route('/pages/protocol', methods=['POST', 'GET'])
def _pages_protocol(): 
    return application.response(request, pages.protocol.Page, None, [POSTGRES])
@app.route('/pages/protocol.<fn>', methods=['POST', 'GET'])
def _pages_protocol_fn(fn):
    return application.response(request, pages.protocol.Page, fn, [POSTGRES])
       
import pages.settings
@app.route('/pages/settings', methods=['POST', 'GET'])
@app.route('/pages/settings.<fn>', methods=['POST', 'GET'])
def _pages_settings(fn=None): 
    return application.response(request, pages.settings.Page, fn, [SQLITE, POSTGRES])
