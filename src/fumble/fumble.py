import re

""" regular-expressions-based building blocks for CLI parsing """

__version__ = "0.2.2"
__all__ = [
    "Syntax",
    "Group", "OneOf", "Optional",
    "AnyWord", "Word", "Integer", "Float",
    "Whitespace"
]


class _SyntaxElement():
    concat = " "
    minargs = 1
    maxargs = None

    def __init__(self, *args, name = None, default = None):
        # check constraints
        if (self.maxargs != None) and (self.maxargs == 0) and (len(args) > 0):
            raise ValueError("%s does not take any elements" % self.__class__.__name__)

        if (self.minargs == self.maxargs) and (len(args) != self.minargs):
            raise ValueError("%s takes exactly %d element%s (not %d)" % (
                self.__class__.__name__, self.minargs, "s" if self.minargs != 1 else "", len(args)
            ))

        if (len(args) < self.minargs):
            raise ValueError("%s takes at least %d element%s (not %d)" % (
                self.__class__.__name__, self.minargs, "s" if self.minargs > 1 else "", len(args)
            ))

        if (self.maxargs != None) and (len(args) > self.maxargs):
            raise ValueError("%s takes at most %d element%s (not %d)" % (
                self.__class__.__name__, self.maxargs, "s" if self.maxargs > 1 else "", len(args)
            ))

        if (name == None) and (default != None):
            raise ValueError("%s must be named to have a default" % self.__class__.__name__)

        if isinstance(default, int):
            if (default < 1) or ((self.maxargs != None) and (default > self.maxargs)):
                raise ValueError("default index must be between 1 and %d" % self.maxargs)
            if not isinstance(args[default-1], (Token, str)):
                raise ValueError("default index must be of type Token or str (not %s)" % args[default-1].__class__.__name__)

        # get defaults (including those of children)
        if (name == None or default == None):
            self._defaults = dict()
        else:
            if isinstance(default, int):
                dflt = args[default-1]
                if isinstance(dflt, Token):
                    self._defaults = { str(name): dflt._plain }
                elif isinstance(dflt, str):
                    self._defaults = { str(name): dflt }
            else:
                self._defaults = { str(name): str(default) }

        for a in args:
            if isinstance(a, _SyntaxElement):
                self._defaults.update(a.defaults)


        # "compile" regexp
        if "_generic_re" in self.__class__.__dict__:
            # this is a simple subclass with a static definition of
            # re - use this rather than overwriting it
            re = self._generic_re
        else:
            # build re from children
            re = ""
            for a in args:
                if len(re) > 0:
                    re += self.concat
                if isinstance(a, _SyntaxElement):
                    re += a.re
                else:
                    re += "(?:%s)" % str(a)

        if name:
            self._re = "(?P<%s>%s)" % (name, re)
        elif len(args) > 1:
            self._re = "(?:%s)" % re
        else:
            self._re = re

    def __add__(self, other):
        return "%s%s%s" % (self, self.concat, other)

    def __str__(self):
        return self._re

    get_regexp = __str__
    re = property(get_regexp)

    def get_defaults(self):
        return self._defaults
    defaults = property(get_defaults)


class Group(_SyntaxElement):
    concat = " "
    minargs = 2


class OneOf(_SyntaxElement):
    concat = "|"
    minargs = 2


class Optional(_SyntaxElement):
    concat = " "
    minargs = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._re += "?"


class Token(_SyntaxElement):
    minargs = 1
    maxargs = 1

    def __init__(self, *args, **kwargs):
        if len(args) > 0 and isinstance(args[0], _SyntaxElement):
            raise ValueError("%s does not accept _SyntaxElement as argument" % self.__class__.__name__)

        try:
            super().__init__(*args, **kwargs)
        except:
            raise
        else:
            self._plain = str(args[0]) if len(args) > 0 else ""


class AnyWord(Token):
    _generic_re = r"[\w\-]+"
    minargs = 0
    maxargs = 0

    def __init__(self, *args, **kwargs):
        if ("default" in kwargs) and isinstance(kwargs["default"], int):
            raise ValueError("%s does not accept an index as default" % self.__class__.__name__)

        try:
            super().__init__(*args, **kwargs)
        except:
            raise


class Word(Token):
    minargs = 1
    maxargs = 1

    def __init__(self, *args, name = None):
        try:
            super().__init__(*args, name = name)
        except:
            raise


class Integer(Token):
    _generic_re = r"[+-]?(?<!\.)\b[0-9]+\b(?!\.[0-9])"
    minargs = 0
    maxargs = 0


class Float(Token):
    _generic_re = r"[+-]?\b[0-9]+\.[0-9]+([eE][0-9])?\b(?!\D)"
    minargs = 0
    maxargs = 0


class Whitespace(Token):
    _generic_re = r"\s+"
    minargs = 0
    maxargs = 0


class Syntax(_SyntaxElement):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._compiled = re.compile(self._re, re.VERBOSE)

    def match(self, text):
        m = self._compiled.fullmatch(text.strip())
        if m != None:
            res = m.groupdict()
            for k in iter(res):
                if res[k] == None:
                    res[k] = self._defaults.get(k)
            return res
        else:
            return None

