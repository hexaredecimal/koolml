
//import {List} from './lib'


class List {
    constructor(items) {
        this.buffer = [];
        for (var item in items) {
            this.buffer.push(item);
        }
    }
}

class App {
    static /* Object */ add(/*Integer*/ left, /*Integer*/ right) {
        return (left);
    }
/*public static void*/ main(args) {
        const /*of type: List */ nums = new List(/*of integer; */[1, 2, 3, 4, 5, 6]);
        const /*of type: String */ name = App.add(new String("ehh, yoh"), new String(" world"));
        console.log(typeof name)
        if (name instanceof String) { return console.log(new String("Its a string")); }
        if (name instanceof List) { return console.log(name); }

    }
}

new App().main(["app"]);
