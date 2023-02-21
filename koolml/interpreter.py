"""
Interpreter
-----------

AST-walking interpreter.
"""
from __future__ import print_function
import operator
from collections import namedtuple
from koolml import ast
from koolml.lexer import Lexer, TokenStream
from koolml.parser import Parser
from koolml.errors import AbrvalgSyntaxError, AbrvalgSyntaxCompileTimeError , report_syntax_error
from koolml.utils import print_ast, print_tokens, print_env
from koolml.types import types, generic_types
from koolml.op import op

BuiltinFunction = namedtuple('BuiltinFunction', ['params', 'body'])
Buffer = str()
Includes = [] 
_lexer = None

class Break(Exception):
    pass


class Continue(Exception):
    pass


class Return(Exception):
    def __init__(self, value):
        self.value = value


class Environment(object):

    def __init__(self, parent=None, args=None, lexer = None):
        self._parent = parent
        self._values = {}
        self.this = None
        self.lexer = lexer
        if args is not None:
            self._from_dict(args)

    def _from_dict(self, args):
        for key, value in args.items():
            self.set(key, value)

    def set(self, key, val):
        self._values[key] = val

    def get(self, key):
        val = self._values.get(key, None)
        if val is None and self._parent is not None:
            return self._parent.get(key)
        else:
            return val

    def asdict(self):
        return self._values

    def __repr__(self):
        return 'Environment({})'.format(str(self._values))


def eval_binary_operator(node, env):
    simple_operations = {
        '+': op.add,
        '-': op.sub,
        '*': op.mul,
        '/': op.div,
        '%': op.mod,
        '>': op.gt,
        '>=': op.ge,
        '<': op.lt,
        '<=': op.le,
        '==': op.eq,
        '!=': op.ne,
        '..': range,
        '...': lambda start, end: range(start, end + 1),
    }
    lazy_operations = {
        '&&': lambda lnode, lenv: eval_expression(lnode.left, lenv) + " && " + eval_expression(lnode.right, lenv),
        '||': lambda lnode, lenv: eval_expression(lnode.left, lenv) + " || " + eval_expression(lnode.right, lenv),
    }
    if node.operator in simple_operations:
        return simple_operations[node.operator](eval_expression(node.left, env), eval_expression(node.right, env))
    elif node.operator in lazy_operations:
        return lazy_operations[node.operator](node, env)
    else:
        raise Exception('Invalid operator {}'.format(node.operator))


def eval_unary_operator(node, env):
    operations = {
        '-': operator.neg,
        '!': operator.not_,
    }
    return operations[node.operator](eval_expression(node.right, env))


def eval_assignment(node, env):
    if isinstance(node.left, ast.SubscriptOperator):
        return eval_setitem(node, env)
    else:
        token, value = node.left.value, eval_expression(node.right, env)
        name = token.value
        line = token.line
        column = token.column+1
        message = 'variable re-assignments are not part of the language.' 
        err = AbrvalgSyntaxCompileTimeError(message, line, column)
        report_syntax_error(env.lexer, err, len(name))


def eval_condition(node, env):
    cond = eval_expression(node.test, env)
    str = 'if (' + cond + ') {'
    if isinstance(node.if_body, list):
        for stmt in node.if_body:
            str += '\n\t\t' + eval_statement(stmt, env)
        str += '\n\t}'
    else:
        str += 'return ' + eval_expression(node.if_body, env) + ';}'

    if node.else_body:
        str += "\n\telse {"
        if isinstance(node.else_body, list):
            for stmt in node.else_body:
                str += "\n\t\t" + eval_statement(stmt, env)
        else:
            str += "return (" + eval_expression(node.else_body, env) + "); "

        str += "\n}"

    return str

def eval_num_match(var, node, env):
    str = ""
    el = None
    for patt in node:
        match = patt
        pattern = match.pattern 
        if not isinstance(pattern, ast.Number):
            if isinstance(pattern, ast.Identifier) and pattern.value.value == "_":
                el = pattern.value.value
            else:
                token = pattern.value
                name = token.value
                line = token.line 
                column = token.column
                message = 'Expected numeric pattern matching, but received Identifier "' + name + '"'
                err = AbrvalgSyntaxCompileTimeError(message, line, column)
                report_syntax_error(env.lexer, err, len(name))

        if not el:
            ptn = eval_expression(pattern, env)
            str += "if (" + var + "==" + ptn + ") {\n" 
        else:
            str += "else {\n"
        if isinstance(match.body, list):
            for stmt in match.body:
                str += "\t" + eval_statement(stmt, env) + "\n"
            str += "}\n"
        else:
            str += "\treturn (" + eval_expression(match.body, env) + ");\n}\n"

    return str
        


def eval_list_match(var, node, env):
    var_name = var.value

    str = ""
    el = None
    li_sep = None
    for patt in node:
        match = patt
        pattern = match.pattern 
        if not isinstance(pattern, ast.Array):
            if isinstance(pattern, ast.Identifier) and pattern.value.value == "_":
                el = pattern.value.value

            if isinstance(pattern, ast.List):
                head_token =  pattern.head
                rest_token =  pattern.rest 
                head = head_token.value
                rest = rest_token.value
                env.set(head, head_token)
                env.set(rest, rest_token)
                var_name = ""
                
                if isinstance(var, ast.Identifier):
                    var_name = var.value.value
                    eval_identifier(var, env)
                    n = env.get(var_name)
                    first_type = get_base_type(n.type_name)
                    

                #li_sep = "%s %s = %s.getFirst();\n%s.removeFirst();\nList %s = %s;" % (first_type , head, var_name, var_name, rest, parse_type(n.type_name), var_name)
                li_sep = "{} {} = ({}) {}.getFirst();\n".format(first_type, head, first_type, var.value.value)
                li_sep += "{}.removeFirst();\n".format(var.value.value)
                li_sep += "{} {} = {};\n".format(parse_type(n.type_name), rest, var.value.value)
                li_sep += "if (%s != null && %s.size() >0 ) {" % (head, rest)
                el = "else ({} != null) ".format(head) + "{" + "return {};".format(head) + "}"
        
            else:
                token = pattern.value
                name = token.value
                line = token.line 
                column = token.column
                message = 'Expected list pattern matching, but received "' + name + '"'
                err = AbrvalgSyntaxCompileTimeError(message, line, column)
                report_syntax_error(env.lexer, err, len(name))

        if not el:
            ptn = eval_expression(pattern, env)
            if len(pattern.items) == 0:
                str += "if (" + var.value.value + ".isEmpty() == true) {"
            else:
                ptn = eval_expression(pattern, env)
                str += "if (" + var.value.value + ".contains(" + ptn + ") == true) {" 
        elif li_sep:
            str += li_sep
        else:
            str += "else {\n"
        
        if isinstance(match.body, list):
            for stmt in match.body:
                str += "\t" + eval_statement(stmt, env) + "\n"
            str += "}\n"
        else:
            str += "\treturn (" + eval_expression(match.body, env) + "); }\n" 
            
    return str  

def eval_type_match(var, node, env):
    str = '' 
    for patt in node:
        pattern = patt.pattern

        if isinstance(pattern, ast.Identifier):
            if pattern.value.value in types or pattern.value.value in generic_types.keys():
                id = pattern.value
                name = id.value
                str += 'if ({} instanceof {})'.format(var, name) + '{'
                body = eval_expression(patt.body, env)
                str += "return {};".format(body) + '}\n'
            else:
                id = pattern.value
                name = id.value
                line = id.line
                column = id.column +1
                err = "Expected a type pattern but found an identifier"
                error = AbrvalgSyntaxCompileTimeError(err, line, column)
                report_syntax_error(env.lexer, error, len(name))

    return str 

def eval_match(node, env):
    expr = eval_expression(node.test, env)

    # test = eval_expression(node.test, env)
    for patt in node.patterns:
        match = patt
        pattern = match.pattern 

        if isinstance(pattern, ast.Number):
            return eval_num_match(expr, node.patterns, env)
        elif isinstance(pattern, ast.Array):
            return eval_list_match(node.test, node.patterns, env)
        elif isinstance(pattern, ast.Identifier):
            if pattern.value.value in types or pattern.value.value in generic_types.keys():
                return eval_type_match(expr, node.patterns, env)


def eval_while_loop(node, env):
    while eval_expression(node.test, env):
        try:
            eval_statements(node.body, env)
        except Break:
            break
        except Continue:
            pass


def eval_for_loop(node, env):
    var_name = node.var_name
    collection = eval_expression(node.collection, env)
    
    env.set(var_name, node)
    ret = ""
    if isinstance(node.collection, ast.Identifier):
        var = env.get(node.collection.value.value)
        if not isinstance(var.value, ast.Array):
            err = "{} is not a symbol of type List<?>".format(node.collection.value.value)
            line = node.collection.value.line
            column = node.collection.value.column
            err = AbrvalgSyntaxCompileTimeError(err, line, column)
            report_syntax_error(env.lexer, err, len(node.collection.value.value))

        _type = var.type_name 
        ret += "for ({} {}: {})".format("Object", var_name, node.collection.value.value)

        # body = eval_statements(node.body, env)
        body = ""

        for stmt in node.body:
            if isinstance(stmt, ast.TypedVariable):
                if isinstance(stmt.value, ast.Identifier):
                    val = stmt.value.value.value
                    if val == var_name:
                        if env.get(stmt.name.value):
                            ln = stmt.name.line
                            cl = stmt.name.column 
                            err = AbrvalgSyntaxCompileTimeError("Symbol is not declared ", ln , cl)
                            report_syntax_error(env.lexer, err, len(stmt.name.value))
                        else:
                            check_type_exists(stmt.type_name, env.lexer)
                            _type = get_base_type(stmt.type_name)
                            env.set(stmt.name.value, stmt)
                            body += "{} {} = ({}) {};".format(_type, stmt.name.value, _type, val)

            else:
                body += "\n" + eval_statement(stmt, env) + ";"
        ret += "{\n" + "{}".format(body) + "\n}\n"

    
    return ret

def eval_instance(node, env):
    ret = "new " + eval_call(node.value, env)
    return ret

def eval_typed_var(node, env):
    _type = node.type_name.name
    _name =  node.name 
    env.set(_name.value, node)
    is_type_valid = check_type_exists(node.type_name, env.lexer)
    if is_type_valid:
        
        val = _type.value
        if _type.value == 'Any':
            val = 'Object'
        
        if node.value != None:
            if isinstance(node.value, ast.Array):
                _value = eval_array(node.value, env, node.type_name)
            else:
                _value = eval_expression(node.value, env)

            return "const /*of type: {} */ {} = {};".format(val, _name.value, _value)
        else:
            return "const /*of type: {}(Infered)*/ {};".format(val, _name.value)

def count_args(gen_type, c = 0):
    if len(gen_type.args) > 0:
        c += 1
        return count_args(gen_type.args[0], c)
    else:
        return c

def check_type_exists(_type, lexer):
    t = _type.name
    val = t.value
    if val == 'Any':
        val = 'Object'

    if val in types:
        return True

    if val in generic_types:
        ret_type = generic_types[val]
        args = count_args(_type)
        expr = ret_type['args_n']

        if args != expr:
            message = "Generic type expects {} parentesized types but {} were given".format(expr, args)
            err = AbrvalgSyntaxCompileTimeError(message, t.line, t.column)
            report_syntax_error(lexer, err, )
        return True

    err = AbrvalgSyntaxError('%s is not a valid type' % (val), t.line, t.column)
    report_syntax_error(lexer, err, len(val))
    

def eval_module_definition(node, env):
    name = node.name.value
    env.this = name
    mod = "class %s {" % (name)
    
    for stmt in node.body:
        ret = eval_statement(stmt, env)
        mod = mod + "\n" + ret 

    mod = mod + "\n}"

    return mod

def parse_type(typ):
    res = typ.name.value
    if typ.args != []:
        arg = typ.args[0]
        return res + '<' + parse_type(arg) + '>'
    else:
        return res 

def get_base_type(typ):
    res = typ.name.value
    if typ.args != []:
        arg = typ.args[0]
        return parse_type(arg)
    else:
        return res 


def eval_function_declaration(node, env):
    
    ret_type = node.ret_type
    if ret_type:
        check_type_exists(ret_type, env.lexer)
    name = node.name 
    header = ""
    if name == 'main':
        header = "/*public static void*/ main(args) {"
    else:
        if ret_type:
            header = 'static /*' + ret_type.name.value+ ' */ ' + name + '('
        else:
            header = "static /* Object */ " + name + "("
    
    # e = Environment()
    # e.lexer = env.lexer
    env.set(name, node)
    
    if name != 'main':
        length = len(node.params)
        if length == 0:
            header = header + ') {'

        for i in range(0, length):
            param = node.params[i]
            _name = ""
            _type = "Object"

            if isinstance(param, ast.TypedParam):
                _name = param.name.value
                _type = param.type_name
                check_type_exists(_type, env.lexer)
                if _type.args != []:
                    _type = parse_type(_type)
                else:
                    _type = _type.name.value
            elif isinstance(param, ast.UntypedParam):
                if i == 0 and param.name == '_':
                    header = "public <T> " + name + "("
                    continue
                else:
                    _name = param.name.value

                    # print('TODO: interpreter.py line 223')
                    # exit(0)

            env.set(_name, param)
            p = "/*" + _type + "*/ " + _name 
            if i == length - 1:
                header = header + p + ") {"
            else:
                header = header + p + ", "

    
    for stmt in node.body:
        if isinstance(stmt, ast.Call):
            ret = eval_call(stmt, env) + ";"
        else:     
            ret = eval_statement(stmt, env)

        if ret:
            header = header + "\n\t" + ret
    header = header + '\n}'
    return header


def eval_call(node, env):
    token = node.left.value
    name = token.value
    line = token.line
    column = token.column +1

    call =  name + '('
    fx = env.get(name)
    
    if not fx:
        message = "Function %s is not defined " % (name)
        err = AbrvalgSyntaxCompileTimeError(message, line, column)
        report_syntax_error(env.lexer, err, len(name))

    if isinstance(fx, ast.Function):
        expected_len = len(fx.params)
        length = len(node.arguments)
        
        if expected_len != length:
            message = "Expected " + str(expected_len) + " argument(s) to be passed to function " + name + ", but received " + str(length) + " arguments" 
            err = AbrvalgSyntaxCompileTimeError(message, line,column)
            report_syntax_error(env.lexer, err, len(name))

        for i in range(0, length):
            arg = node.arguments[i]
            arg = eval_expression(arg, env)
            if i == length -1:
                call = call + arg + ')'
            else:
                call = call + arg + ','
        call = '{}.{}'.format(env.this, call)
    elif isinstance(fx, ast.Builtin):
        call = "{}".format(fx.signature)
        length = len(node.arguments)
        for i in range(0, length):
            arg = node.arguments[i]
            arg = eval_expression(arg, env)
            if i == length -1:
                call += arg 
            else:
                call += arg + ','

            call += ')'


        
    # call = call + ")"
    return call
    # function = eval_expression(node.left, env)
    # n_expected_args = len(function.params)
    # n_actual_args = len(node.arguments)
    # if n_expected_args != n_actual_args:
    #     raise TypeError('Expected {} arguments, got {}'.format(n_expected_args, n_actual_args))
    # args = dict(zip(function.params, [eval_expression(node, env) for node in node.arguments]))
    # if isinstance(function, BuiltinFunction):
    #     return function.body(args, env)
    # else:
    #     call_env = Environment(env, args)
    #     try:
    #         return eval_statements(function.body, call_env)
    #     except Return as ret:
    #         return ret.value


def eval_identifier(node, env):
    token = node.value
    name = token.value
    line = token.line 
    column = token.column
    
    val = env.get(name)
    if val is None:
        err = AbrvalgSyntaxCompileTimeError("Identifier " + name + " is not defined", line, column)
        report_syntax_error(env.lexer, err, len(name))
    return name


def eval_getitem(node, env):
    collection = eval_expression(node.left, env)
    key = eval_expression(node.key, env)
    return collection[key]


def eval_setitem(node, env):
    collection = eval_expression(node.left.left, env)
    key = eval_expression(node.left.key, env)
    collection[key] = eval_expression(node.right, env)


def eval_array(node, env, head=None):
    items = node.items

    ret = ""
    if head:
        ret += "new List("
        ret += "/*of {}; */".format(get_base_type(head))

    else:
        ret += "new List( /* of infered object */"

    ret += '['
    for i in range(0, len(items)) :
        res = eval_expression(items[i], env)
        
        if i == len(items) -1:
            ret += res + "])"
        else:
            ret +=res + ","
    return ret


def eval_dict(node, env):
    return {eval_expression(key, env): eval_expression(value, env) for key, value in node.items}


def eval_return(node, env):
    return "return (" + eval_expression(node.value, env) + ");" if node.value is not None else "; "


evaluators = {
    ast.Number: lambda node, env: str(node.value),
    ast.String: lambda node, env: "new String(\"%s\")" % (node.value),
    ast.Array: eval_array,
    ast.Dictionary: eval_dict,
    ast.Identifier: eval_identifier,
    ast.BinaryOperator: eval_binary_operator,
    ast.UnaryOperator: eval_unary_operator,
    ast.SubscriptOperator: eval_getitem,
    ast.Assignment: eval_assignment,
    ast.Condition: eval_condition,
    ast.Match: eval_match,
    ast.WhileLoop: eval_while_loop,
    ast.ForLoop: eval_for_loop,
    ast.Function: eval_function_declaration,
    ast.Module: eval_module_definition,
    ast.Call: eval_call,
    ast.Return: eval_return,
    ast.TypedVariable: eval_typed_var, 
    ast.Instance: eval_instance
}


def eval_node(node, env):
    tp = type(node)
    if tp in evaluators:
        return evaluators[tp](node, env)
    else:
        raise Exception('Unknown node {} {}'.format(tp.__name__, node))


def eval_expression(node, env):
    return eval_node(node, env)


def eval_statement(node, env):
    return eval_node(node, env)


def eval_statements(statements, env):
    ret = ""
    result = ""
    for statement in statements:
        if isinstance(statement, ast.Break):
            raise Break(ret)
        elif isinstance(statement, ast.Continue):
            raise Continue(ret)
        r = eval_statement(statement, env) 
        if r:
            ret += r + "\n"
        if isinstance(statement, ast.Return):
            raise Return(ret)
    return ret


def add_builtins(env):
    builtins = {
        # 'print': (['value'], lambda args, e: print(args['value'])),
        # 'len': (['iter'], lambda args, e: len(args['iter'])),
        # 'slice': (['iter', 'start', 'stop'], lambda args, e: list(args['iter'][args['start']:args['stop']])),
        # 'str': (['in'], lambda args, e: str(args['in'])),
        # 'int': (['in'], lambda args, e: int(args['in'])),
        'print': ast.Builtin('console.log('),
        'println': ast.Builtin('console.log('), 
        'readline': ast.Builtin('prompt()'),
        'readInt': ast.Builtin('ParseInt(prompt())'),
        'true': ast.Identifier('true'),
        'false': ast.Identifier('false')
    }
    for key, param in builtins.items():
        env.set(key, param)



def create_global_env():
    env = Environment()
    add_builtins(env)
    return env


def evaluate_env(s, env, verbose=False):
    lexer = Lexer()
    env.lexer = lexer
    try:
        tokens = lexer.tokenize(s)
    except AbrvalgSyntaxError as err:
        report_syntax_error(lexer, err)
        if verbose:
            raise
        else:
            return

    if verbose:
        print('Tokens')
        print_tokens(tokens)
        print()

    
    token_stream = TokenStream(tokens)

    try:
        program = Parser(lexer).parse(token_stream)
    except AbrvalgSyntaxError as err:
        report_syntax_error(lexer, err)
        if verbose:
            raise
        else:
            return

    if verbose:
        print('AST')
        print_ast(program.body)
        print()

    ret = eval_statements(program.body, env)


    if verbose:
        print('Environment')
        print_env(env)
        print()

    return ret


def evaluate(s, verbose=False):
    return evaluate_env(s, create_global_env(), verbose)
