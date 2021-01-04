import sys, os, pickle, json

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    COMMENT = '\033[90m'

def help(text):
    return '\033[92m' + str(text) + '\033[0m'

def error(text):
    return '\033[91m' + str(text) + '\033[0m'

def header(text):
    return '\033[1m' + str(text) + '\033[0m'

def print_comment(text):
    if text is not None:
        print('\033[90m' + str(text) + '\033[0m')
def print_error(text):
    if text is not None:
        print('\033[91m' + str(text) + '\033[0m')
def print_header(text):
    if text is not None:
        print('\033[1m' + str(text) + '\033[0m')
def print_warning(text):
    if text is not None:
        print('\033[93m' + str(text) + '\033[0m')
def print_help(text):
    if text is not None:
        print('\033[92m' + str(text) + '\033[0m')

def arg(n):
    try:
        return sys.argv[n]
    except:
        return None

class Console:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    COMMENT = '\033[90m'
    def __init__(self, FILE = None):
        self.defaults_file = '/DOMINO/data/console.defaults'
        os.makedirs('/DOMINO/data', exist_ok=True)
        if os.path.isfile(self.defaults_file):
            with open(self.defaults_file) as f:
                self.defaults = json.load(f)
        else:
            self.defaults = {}
    def arg(self, n):
        try:
            return sys.argv[n]
        except:
            return None
    @staticmethod
    def print_comment(text):
        if text is not None:
            print('\033[90m' + str(text) + '\033[0m')
    @staticmethod
    def print_error(text):
        if text is not None:
            print('\033[91m' + str(text) + '\033[0m')
    @staticmethod
    def print_header(text):
        if text is not None:
            print('\033[1m' + str(text) + '\033[0m')
    @staticmethod
    def print_warning(text):
        if text is not None:
            print('\033[93m' + str(text) + '\033[0m')
    @staticmethod
    def print_help(text):
        if text is not None:
            print('\033[92m' + str(text) + '\033[0m')

    def error(self, msg):
        print_error(msg)
        sys.exit()

    def warning(self, msg):
        print_warning(msg)
        
    def comment(self, msg):
        print_comment(msg)

    def help(self, msg):
        print_help(msg)

    def set_default(self, prompt, value):
        self.defaults[str(prompt)] = value
        with open(self.defaults_file, 'w') as f:
            json.dump(self.defaults, f)
    
    def input(self, prompt, default = None):
        if default is None:
            default = self.defaults.get(str(prompt))
        if default is None:
            default = ''
        value = input(f'{prompt} [{default}] ? ')
        if value.strip() == '':
            return default
        else:
            self.set_default(prompt, value)
            return value

    def run(self, product, version, proc, params):
        program = f'/DOMINO/products/{product}/{version}/python/{proc}.py'
        if os.path.exists(program):
            args = " ".join(params)
            command = f'python3.6 {program} {args}'
            print_comment(command)
            os.system(command)
    
    def system(self, cmd):
        self.comment(cmd)
        os.system(cmd)
        


