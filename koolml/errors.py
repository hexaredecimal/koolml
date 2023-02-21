"""
Errors
------

Exceptions and exception helpers.
"""


class AbrvalgSyntaxError(Exception):

    def __init__(self, message, line, column):
        super(AbrvalgSyntaxError, self).__init__(message)
        self.error = "SyntaxError"
        self.message = message
        self.line = line
        self.column = column

class AbrvalgSyntaxCompileTimeError(Exception):
    def __init__(self, message, line, column):
        super(AbrvalgSyntaxCompileTimeError, self).__init__(message)
        self.error = "CompileTimeError"
        self.message = message
        self.line = line
        self.column = column


def report_syntax_error(lexer, error, length=1):
    line = error.line
    column = error.column
    source_line = lexer.source_lines[line - 1]
    print('\033[91m{}\033[0m: {} at line {}, column {}'.format(error.error, error.message, line, column))
    print('{} | {}\n{}\033[91m{}\033[0m'.format(line, source_line, ' ' * (column + 3), '^' * length))
    exit(4)
    

