import json

def createMod(name, imp, isgen=False, args=0):
    return {
        'name': name, 
        'include': imp, 
        'generic': isgen,
        'args_n': args
    }

mods = [
    createMod('List', 'java.util.List', True, 1)
]

m = json.dumps(mods)
with open('modules.json', 'w') as f:
    f.write(m)