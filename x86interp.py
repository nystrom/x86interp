#!/usr/bin/env python
# This is a simple, very incomplete, x86 assembly code interpreter. It supports only a few instructions and makes
# many possibly incorrect assumptions about the runtime environment. It only suports 32-bit assembly.
# The code is largely a hack and should be reimplemented more cleanly.
#
# usage:
# python x86interp.py file.s ...
#
import sys
import re

# instruction operands
class Operand(object):
  pass

# labels
class Label(Operand):
  def __init__(self, x86, name):
    self.x86 = x86
    self.name = name

  def __str__(self):
    return self.name

# immediates
class Imm(Operand):
  def __init__(self, x86, value):
    self.x86 = x86
    self.value = value

  def read(self):
    return self.value

  def __str__(self):
    return '$' + str(self.value)

# registers (including virtual registers)
class Reg(Operand):
  def __init__(self, x86, name):
    self.x86 = x86
    self.name = name

  def read(self):
    if self.name in self.x86.regs:
      return self.x86.regs[self.name]
    else:
      return None

  def write(self, value):
    self.x86.regs[self.name] = value

  def __str__(self):
    return '%' + self.name

# memory references
class Mem(Operand):
  def __init__(self, x86, offset, base):
    self.x86 = x86
    self.offset = offset
    self.base = base

  def read(self):
    key = '%08x' % (self.offset + self.base.read())
    if key in self.x86.mem:
      return self.x86.mem[key]
    else:
      return None

  def write(self, value):
    key = '%08x' % (self.offset + self.base.read())
    self.x86.mem[key] = value

  def __str__(self):
    return '%d(%s)' % (self.offset, str(self.base))

# instructions
class Insn(object):
  def __init__(self, opc, args):
    self.opc = opc
    self.args = args

  def __str__(self):
    return self.opc + ' ' + str(map(str, self.args))

# the interpreter itself
class X86Interpreter(object):
  def __init__(self):
    self.lines = []
    self.labels = dict()
    self.mem = dict()
    self.regs = {
        'eax':          0x5a5a5a5a,
        'ecx':          0x5a5a5a5a,
        'edx':          0x5a5a5a5a,
        'ebx':          0x5a5a5a5a,
        'esp':          0xbffff510,
        'ebp':          0xbffff518,
        'esi':          0x5a5a5a5a,
        'edi':          0x5a5a5a5a,
        'eflags':       0x282,
        'cs':           0x1b,
        'ss':           0x23,
        'ds':           0x23,
        'es':           0x23,
        'fs':           0x0,
        'gs':           0xf,
    }

  def eval_function(self, sym):
    if sym in self.labels:
      eip = self.labels[sym]
    elif isinstance(sym, int):
      eip = sym
    else:
      print 'invalid function ' + str(sym)
      eip = None

    while eip != None:
      # print eip
      eip = self.eval_pc(eip)

  def eval_pc(self, eip):
    # if we fall off the end, return
    if eip >= len(self.lines):
      return None

    line = self.lines[eip]

    r = None
    if line:
      r = self.parse(line)

    if isinstance(r, Insn):
      if r.opc == 'movl':
        r.args[1].write(r.args[0].read())
        return eip + 1
      elif r.opc == 'incl' or r.opc == 'inc':
        r.args[0].write(r.args[0].read() + 1)
        return eip + 1
      elif r.opc == 'decl' or r.opc == 'dec':
        r.args[0].write(r.args[0].read() - 1)
        return eip + 1
      elif r.opc == 'addl' or r.opc == 'add':
        r.args[1].write(r.args[1].read() + r.args[0].read())
        return eip + 1
      elif r.opc == 'negl' or r.opc == 'neg':
        r.args[0].write(-r.args[0].read())
        return eip + 1
      elif r.opc == 'subl' or r.opc == 'sub':
        r.args[1].write(r.args[1].read() - r.args[0].read())
        return eip + 1
      elif r.opc == 'imull' or r.opc == 'imul':
        if len(r.args) == 1:
          eax = Reg(self, 'eax')
          edx = Reg(self, 'edx')
          result = r.args[0].read() * eax.read()
          lo = result & 0xffffffff
          hi = (result >> 32) & 0xffffffff
          eax.write(lo)
          edx.write(hi)
        elif len(r.args) == 2:
          result = r.args[1].read() * r.args[0].read()
          lo = result & 0xffffffff
          r.args[1].write(lo)
        elif len(r.args) == 3:
          result = r.args[1].read() * r.args[0].read()
          lo = result & 0xffffffff
          r.args[2].write(lo)
        else:
          raise Exception('bad imul instruction: ' + r)
        return eip + 1
      elif r.opc == 'popl':
        esp = Reg(self, 'esp')
        star_esp = Mem(self, 0, esp)
        r.args[0].write(star_esp.read())
        esp.write(esp.read() + 4)
        return eip + 1
      elif r.opc == 'pushl':
        esp = Reg(self, 'esp')
        star_esp = Mem(self, 0, esp)
        esp.write(esp.read() - 4)
        star_esp.write(r.args[0].read())
        return eip + 1
      elif r.opc == 'leave':
        ebp = Reg(self, 'ebp')
        esp = Reg(self, 'esp')
        star_esp = Mem(self, 0, esp)
        # movl ebp, esp
        esp.write(ebp.read())
        # popl ebp
        ebp.write(star_esp.read())
        esp.write(esp.read() + 4)
        return eip + 1
      elif r.opc == 'ret':
        esp = Reg(self, 'esp')
        star_esp = Mem(self, 0, esp)
        # popl eip
        eip = star_esp.read()
        esp.write(esp.read() + 4)
        return eip
      elif r.opc == 'call':
        label = r.args[0]
        if isinstance(label, Label):
          name = label.name
          esp = Reg(self, 'esp')
          star_esp = Mem(self, 0, esp)
          if name == '_input' or name == 'input':
            eax = Reg(self, 'eax')
            eax.write(input())
            return eip + 1
          elif name == '_print_int' or name == 'print_int':
            print star_esp.read(),
            return eip + 1
          elif name == '_print_int_nl' or name == 'print_int_nl':
            print star_esp.read()
            return eip + 1
          else:
            # push eip
            esp.write(esp.read() - 4)
            star_esp.write(eip)
            return self.labels[label.name]
        else:
          raise Exception('bad label ' + str(label))
      else:
        raise Exception('unknown instruction ' + r.opc)
    else:
      return eip + 1

  def parse_op(self, op, opc=None):
    if op.startswith('$'):
      return Imm(self, int(op[1:]))
    elif op.startswith('%'):
      return Reg(self, op[1:])
    elif op.startswith('(') and op.endswith(')'):
      return Mem(self, 0, self.parse_op(op[1:-1]))
    else:
      m = re.search(r'^(-?\d+)\((.*)\)$', op)
      if m:
        return Mem(self, int(m.group(1)), self.parse_op(m.group(2)))
      else:
        m = re.search(r'^((\w|\$)+)$', op)
        if m:
          name = m.group(1)
          functions = ['input', '_input',
                       'print_int_nl', '_print_int_nl',
                       'print_int', '_print_int']
          if name in self.labels or name in functions:
            return Label(self, name)
          else:
            # virtual register
            return Reg(self, name)
        else:
          raise Exception('unrecognized operand ' + op)

  def parse(self, line):
    if line.startswith('.'):
      return None
    if self.label(line):
      return None
    r = re.split(r',?\s*', line)
    return Insn(r[0], map(lambda op: self.parse_op(op, r[0]), r[1:]))

  def label(self, line):
    m = re.search(r'^((\w|\$)+):$', line)
    if m:
      sym = m.group(1)
      return sym
    return None

  def load(self, code):
    self.lines += code.split('\n')
    for i, line in enumerate(self.lines):
      line = re.sub(r'#.*', '', line)
      line = re.sub(r'//.*', '', line)
      line = re.sub(r'^\s+', '', line)
      line = re.sub(r'\s+$', '', line)
      line = re.sub(r'\s+', ' ', line)
      label = self.label(line)
      if label:
        self.labels[label] = i
      
      # should parse line here
      self.lines[i] = line

def main():
  # create an interpreter object
  x86 = X86Interpreter()

  # load all the assembly files
  for filename in sys.argv[1:]:
    f = open(filename, 'r')
    x86.load(f.read())

  # run _main or main
  if '_main' in x86.labels:
    x86.eval_function('_main')
  elif 'main' in x86.labels:
    x86.eval_function('main')
  else:
    print 'symbol _main or main not found'
    print 'starting from the first instruction'
    x86.eval_function(0)

if __name__ == "__main__":
  main()
