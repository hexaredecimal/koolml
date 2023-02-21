import json

builtin = True 
types = {
    'Object': builtin,
    'Integer': builtin, 
    'Double': builtin, 
    'String': builtin,
    'Character': builtin, 
    'Boolean': builtin
}


generic_types = {
}



def readMods():
    src = "./etc/modules.json"
    with open(src, 'r') as f:
        f = f.read()
    obj = json.loads(f)    
    for o in obj:
        name = o['name']
        include = o['include']
        gen = o['generic']
        args_n = o['args_n']

        generic_types[name] = o

readMods()
