from domino.databases.oracle import HexToRaw

YES = HexToRaw('07D2000307D20002')
NO = HexToRaw('07D2000307D20001')

def YesNo(id, default=None):
    if id:
        if id == YES:
            return True
        elif id == NO:
            return False
    return default

