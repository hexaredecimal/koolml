# koolml

## koolml is a meta-lang inspired programming language that compiles to **javascript**


## Features:
- Regular expression based lexer
- Top-down recursive descent parser
- AST-walking interpreter
- REPL
- Javascript codegen
- Static typing

## Known bugs 
- String concat doesn't create a string, but a derived type of string 
- ```js 
    const x = new String("Hello") + new String("World")
    if (x instanceof String) { .... } // This results to false (why? please help)
    ```
- The above doesn't work when matching a result of string concat


## Koolml doesn't require any third-party libraries. 
> ### Built on top of Abrvalg.
> ### Built using python3


## What the language looks like:

```ml
  module App ->
    fun main() ->
      print("Hello, world")
      let greet: String = "Hello, " + "World"
      print(greet)
```

## Aim of this language
- Learning principles of functional programmming from an imperative and OOP standpoint
- Functional programming on the web (on my own terms, no weird syntax and obscure language behavior)
- Create an alternative to JavaScript for using on my School projects (Web and CFB - computing Fundamentals B)



## You can find more examples in ``tests`` directory.

> ## How to try it:

```sh    
    git clone https://github.com/akrylysov/abrvalg.git
    cd koolml
    python -m koolml # starts a REPL
    python -m koolml -r ./test/factorial.ml # compiles the file and runs it using nodejs
    python -m koolml -b ./test/factorial.ml # compiles the file to a javascript file (no running)

