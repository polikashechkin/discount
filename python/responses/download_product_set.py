import io, sqlite3
from domino.core import log
#from discount.product_sets import ProductSet, ProductSetItem
from tables.sqlite.product_set import ProductSet 
from tables.sqlite.good_set_item import GoodSetItem
from tables.Good import Good
from responses import Response as BaseResponse 
from settings import DATABASE_DB

class Response(BaseResponse):
    def __init__(self, application, request):
        super().__init__(application, request)
        self.sqlite = None
        self.postgres = None
        
    def __call__(self):
        set_id = self.get_int('set_id')
        #ps = self.sqlite.query(ProductSet).get(set_id)
        
        # список всех наименований товаров
        good_names = {}
        for good_code, good_name in self.postgres.query(Good.code, Good.name):
            good_names[good_code] = good_name

        # список элементов набора с наименованиями
        items = []
        for item in self.sqlite.query(GoodSetItem).filter(GoodSetItem.set_id == set_id):
            items.append(item)
            item.name = good_names.get(item.code, '')

        stream = io.StringIO()
        #for item in sorted(items, key = item.name):
        for item in items:
            stream.write(f'"{item.code}"\t"{item.name}"\t{item.price if item.price else ""}\n')
        return self.download(stream.getvalue(), file_name='goods.txt')