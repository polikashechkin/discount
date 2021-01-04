from domino.databases.oracle import HexToRaw

vat_on_id = {}

class Vat:
    def __init__(self, ID, value, name):
        self.ID = ID
        self.id = HexToRaw(ID)
        self.value = value
        self.name = name

    def __repr__(self):
        return f'<Vat(id={self.ID}, value={self.value}, name={self.name})>'

    @staticmethod
    def get(id):
        vat = vat_on_id.get(id)
        return vat if vat else default_vat

    @staticmethod
    def all():
        return vats


default_vat = Vat('07D2000501B70003', None, 'без НДС')
vats = [
Vat('07D2000502870001', 18, '18%'),
Vat('07D2000501B70002', 10, '10%'),
Vat('07D2000504030002', 0, '0%'),
default_vat
]

for vat in vats:
    vat_on_id[vat.id] = vat



