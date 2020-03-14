#!/usr/bin/env python3
import os, subprocess

the_arg = os.environ.get("SSH_ORIGINAL_COMMAND")
if not the_arg:
	exit()
elif the_arg.startswith("rsync "):
	subprocess.run(the_arg, shell=True)
	exit()
else:
	exit()
