
from pypeg2 import *
import functools as ft
import itertools as itt
import operator as op

integer = RegEx (r'\d+')

def transparentNew(cls, content=None, *otherargs):
    if len(otherargs)>0:
        raise Error( "Too many arguments for {}: '{}', '{}'"
                .format( cls, content, otherargs))
    return content

class Ref(int):
    grammar = '#', int
    def __repr__(self):
        return "#{}".format(int(self))

class Kw(str):
    grammar = '.', Keyword, '.'

class Qstr(str):
    grammar = "'", RegEx(r"[^']*"), "'"

class Star(str):
    grammar = RegEx (r'[*$]')

class Float(float):
    grammar = RegEx (r'[+-]?\d+\.\d*(?:[eE][+-]?\d+)?')

class Arg:
    grammar = [Ref, Star, Kw, Qstr, Float, int]
    __new__ = transparentNew

def resolvelist(self, d):
    for i in range(len(self)):
        if isinstance (self[i], Ref):
            ref = self[i]
            val = d[ref]
            self[i] = val
            if isinstance (val, (Pjux, Call, Plist)):
                val.resolve(d)

class Plist(list):
    grammar = "(", optional(csl(Arg)), ")"
    resolve = resolvelist

class Call:
    grammar = name(), attr('args', Plist)
    def __repr__(self):
        return "Call: {}(args[{}])".format(self.name, len(self.args))
    def resolve(self, d):
        self.args.resolve(d)

Arg.grammar += [Call, Plist]

class Pjux(list):
    grammar = blank, "(", maybe_some(Call), ")"
    resolve = resolvelist
    def __repr__(self):
        return "Pjux: {}".format(' '.join(map(lambda x:x.name, self)))

class Iob:
    grammar = attr('inx',Ref), '=', attr('val', [Call,Pjux]), ';'
    def __repr__(self):
        return "Iob({}): {}".format(self.inx, self.val)
    def __setattr__(self, key, val):
        self.__dict__[key] = val
    def resolve(self, d):
        d[self.inx] = self.val
        self.val.resolve(d)

attrname = op.attrgetter('name')
attrinx = op.attrgetter('inx')
attrval = op.attrgetter('val')

class Myparser(Parser):

    def __init__(self, filename, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filename = filename

        ##  Index
        self.d = { o.inx:o.val
            for o in self.iobs() }

        ##  Resolve
        for o in self.d.values():
            o.resolve(self.d)

        ##  Group
        calls = (o for o in self.d.values() if isinstance(o, Call))
        scalls = sorted(calls, key=attrname)
        gcalls = itt.groupby(scalls, attrname)
        self.gcalls = {k:list(v) for k,v in gcalls}

    def fullLines(self):
        with open(self.filename) as f:
            chunk = []
            for line in f:
                chunk.append(line)
                if line.strip().endswith(';'):
                    yield ''.join(chunk)
                    chunk = []

    def iobs(self):
        for line in self.fullLines():
            if not line.startswith('#'):
                continue
            rest, result =  self.parse(line, Iob)
            yield result

