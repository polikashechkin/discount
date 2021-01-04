import os, sys, random
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from time import sleep
from domino.cli import Console

def create_ean13(n):
    digits = str(n)
    even = int(digits[1]) + int(digits[3]) + int(digits[5]) + int(digits[7])  + int(digits[9]) + int(digits[11])
    even = even * 3
    odd = int(digits[0]) + int(digits[2]) + int(digits[4]) + int(digits[6]) + int(digits[8]) + int(digits[10]) 
    total = even + odd
    checksum = total % 10
    if checksum != 0 :
        checksum = 10 - checksum
    return f'{digits}{checksum}'

def gen_ean13_codes(prefix, count):
    prefix = int(prefix)
    codes = []
    for i in range(count):
        r = random.randrange(0, 10_000_000)
        code = prefix * 10_000_000 + r
        code = create_ean13(code)
        codes.append(str(code))
    return codes


if __name__ == '__main__':
    codes = gen_ean13_codes('12345', 100)
    for code in codes:
        print(code)
