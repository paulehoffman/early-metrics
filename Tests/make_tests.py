#!/usr/bin/env python3
''' Program to make tests for metrics testing '''

# Text is copied from rssac-047.mkd

# Read all the positive files into memory
in_files = '''
p-dot-dnskey
p-dot-ns
p-dot-soa
p-neg
p-tld-ds
p-tld-ns
'''.strip().splitlines()


p_files = {}
for this_file in in_files:
	p_files[this_file] = open(this_file, mode="rt").readlines()

n_files = {}

# All of the RRsets in the Answer, Authority, and Additional sections match RRsets found in the zone. [vnk]

# Add a new record to Answer
out_text = "# [pmz] Start with p-tld-ds, add a DS before 09E0AF18E54225F87A3B10E95C9DA3F1E58E5B59\n"
for this_line in p_files["p-tld-ds"]:
	if this_line == "        - us. 86400 IN DS 39361 8 1 09E0AF18E54225F87A3B10E95C9DA3F1E58E5B59\n":
		out_text += "        - us. 86400 IN DS 55747 8 2 77806C45DCA415FBD8FDEEA0A436EE68FE6AA5B3C23B4D89E03BBEF3 34FA0CB6\n"  # Taken from .ru DS
	out_text += this_line
n_files["n-vnk-pmz"] = out_text

# Add a new record to Authority 
out_text = "# [zoc] Start with p-tld-ns, add an NS before c.cctld.us.\n"
for this_line in p_files["p-tld-ns"]:
	if this_line == "        - us. 172800 IN NS c.cctld.us.\n":
		out_text += "        - us. 172800 IN NS z.cctld.us.\n"
	out_text += this_line
n_files["n-vnk-zoc"] = out_text

# Add a new record to Additional
out_text = "# [rse] Start with p-tld-ns, add an A for c.cctld.us.\n"
for this_line in p_files["p-tld-ns"]:
	if this_line == "        - c.cctld.us. 172800 IN A 156.154.127.70\n":
		out_text += "        - c.cctld.us. 172800 IN A 156.154.127.99\n"
	out_text += this_line
n_files["n-vnk-rse"] = out_text

# Change a record in Answer
out_text = "# [dxp] Start with p-tld-ds, change DS with 09E0AF18E54225F87A3B10E95C9DA3F1E58E5B59\n"
for this_line in p_files["p-tld-ds"]:
	if this_line == "        - us. 86400 IN DS 39361 8 1 09E0AF18E54225F87A3B10E95C9DA3F1E58E5B59\n":
		out_text += "        - us. 86400 IN DS 39361 8 1 09E0AF18E54225F87A3B10E95C9DA3F1E58EFFFF\n"
	else:
		out_text += this_line
n_files["n-vnk-dxp"] = out_text

# Change a record in Authority
out_text = "# [gye] Start with p-tld-ns, c.cctld.us. to z.cctld.us.\n"
for this_line in p_files["p-tld-ns"]:
	if this_line == "        - us. 172800 IN NS c.cctld.us.\n":
		out_text += "        - us. 172800 IN NS z.cctld.us.\n"
	else:
		out_text += this_line
n_files["n-vnk-gye"] = out_text

# Change a record in Additional
out_text = "# [ykm] Start with p-tld-ns, change A for c.cctld.us.\n"
for this_line in p_files["p-tld-ns"]:
	if this_line == "        - c.cctld.us. 172800 IN A 156.154.127.70\n":
		out_text += "        - c.cctld.us. 172800 IN A 156.154.127.99\n"
	else:
		out_text += this_line
n_files["n-vnk-ykm"] = out_text

# Create the n files
for this_file_name in n_files:
	f = open(this_file_name, mode="wt")
	f.write(n_files[this_file_name])
	f.close()
