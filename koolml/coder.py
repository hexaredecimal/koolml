

ListClass = '''

class List {
    constructor(items) {
        this.buffer = [];
        for (var item in items) {
            this.buffer.push(item);
        }
    }
}

'''

runner = '''
new App().main(["app"]);
'''