#! /usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 Sauce Labs Inc
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# 'Software'), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys
import pprint
import saucerest

from optparse import OptionParser

usage = "usage: %prog [options] <username> <access key> <local host> <local port> <remote port> <remote domain> [<remote domain>...]"
usage = "usage: %prog <username> <access key>"
op = OptionParser(usage=usage)
(options, args) = op.parse_args()
if len(args) != 2:
  op.error("exactly 2 arguments are required")

username = args[0]
access_key = args[1]

pp = pprint.PrettyPrinter()

sauce = saucerest.SauceClient(name=username, access_key=access_key)

pp.pprint(sauce.list_tunnels())
