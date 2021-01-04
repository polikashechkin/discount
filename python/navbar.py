from grants import Grants

def navbar(page):          
    #права = Права(page.request.account_id(), page.request.user_id)
    grants = Grants(page.account_id, page.user_id)
    nav = page.navbar()
    nav.header(f'{page.application.module_name}, версия {page.application.version}', 'pages/start_page')
    if (Grants.BOSS, Grants.ASSISTANT, Grants.DS_MANAGER, Grants.DS_ASSISTANT, Grants.DS_WATCHING, Grants.CARD_MANAGER) in grants:
        nav.item('Типы карт', 'pages/card_types')
    if (Grants.BOSS, Grants.ASSISTANT, Grants.DS_MANAGER, Grants.DS_ASSISTANT, Grants.DS_WATCHING) in grants:
        nav.item('Дисконтные схемы', 'pages/schemas.open')
    if Grants.OPERATOR in grants:
        #nav.item('Анкета', 'pages/questionnaire.open')
        nav.item('Поиск', 'pages/call_center.open')

    if (Grants.BOSS, Grants.SYSADMIN) in grants:
        nav.item('Штатное расписание', 'pages/grants.open')

    if (Grants.BOSS, Grants.ASSISTANT, Grants.DS_MANAGER, Grants.DS_ASSISTANT, Grants.DS_WATCHING, Grants.CARD_MANAGER) in grants:
        nav.item('Чеки', 'pages/fs_checks')
        nav.item('Справки', 'pages/reports')
                
    #group = nav.group('Документация')
    #group.item('Виды карт', 'pages/card_classes')
    #group.item('Типы акции', 'pages/action_types.open')
    
    if Grants.SYSADMIN in grants:
    #    group = nav.group('Sysadmin')
        #group.item('Расчеты', 'pages/calc_checks.open')
        #group.item('Справки', 'pages/reports')
        nav.item('Процедуры', 'domino/pages/procs') 
        #group.item('Отчеты', 'pages/reports.open')
    #    group.item('Протокл работы пользователей', 'pages/protocol')
        #group.item('Задачи', 'jobs')
    #    group.item('Специальные наборы товаров', 'pages/product_sets')
    #    group.item('Утвержденные дисконтные схемы', 'pages/shemes.open')
        #group.item('Настройка', 'pages/settings.open')
        #group.item('Журнал вызовов', 'pages/log_show')
        #group.item('История изменений', 'pages/change_log.open')
    #    group.item('Спецификации обмена', 'https://docs.google.com/document/d/1bPO4wXqwbesi7YskgdUIGrGEZ1jzZFiQ5Jthys4fE-Y/edit?usp=sharing')
