#!/usr/bin/python
# -*- coding: utf8 -*-

#rate limited output

import time
import os
import sys

verbose = False
rate = 200 #lines per seconds

while True:
    try:
        start_blockingio = time.time()
        line = sys.stdin.next()
        end_blockingio = time.time()
        delay = end_blockingio-start_blockingio
        if verbose: 
            sys.stderr.write('took %s s for input, sending in %s s' % (delay,max((1-delay)/rate,0)))
        time.sleep(max(0,(1-delay)/rate))
        print(line)
    except Exception as e:
        exit()
        
    
