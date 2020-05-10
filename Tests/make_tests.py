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

########## Need to check longer, shorter, and different value

# Add a new record to Answer
out_text = "# [ffr] Start with p-dot-ns, add z.root-servers.net\n"
for this_line in p_files["p-dot-ns"]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.\n":
		out_text += "        - . 518400 IN NS z.root-servers.net.\n"
	out_text += this_line
n_files["n-vnk-ffr"] = out_text

# Change a record in Answer
out_text = "# [vpn] Start with p-dot-ns, change a.root-server.net to z.root-servers.net\n"
for this_line in p_files["p-dot-ns"]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.\n":
		out_text = "        - . 518400 IN NS z.root-servers.net.\n"
	else:
		out_text += this_line
n_files["n-vnk-vpn"] = out_text

# Delete a record from Answer
out_text = "# [uuc] Start with p-dot-ns, delete a.root-servers.net\n"
for this_line in p_files["p-dot-ns"]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.\n":
		continue
	out_text += this_line
n_files["n-vnk-uuc"] = out_text

# Add a new record to Authority 
out_text = "# [zoc] Start with p-tld-ns, add z.cctld.us\n"
for this_line in p_files["p-tld-ns"]:
	if this_line == "        - us. 172800 IN NS c.cctld.us.\n":
		out_text += "        - us. 172800 IN NS z.cctld.us.\n"
	out_text += this_line
n_files["n-vnk-zoc"] = out_text

# Change a record in Authority
out_text = "# [gye] Start with p-tld-ns, change c.cctld.us. to z.cctld.us\n"
for this_line in p_files["p-tld-ns"]:
	if this_line == "        - us. 172800 IN NS c.cctld.us.\n":
		out_text = "        - us. 172800 IN NS z.cctld.us.\n"
	else:
		out_text += this_line
n_files["n-vnk-gye"] = out_text

# Delete a a record from Authority
out_text = "# [gut] Start with p-tld-ns, delete c.cctld.us.\n"
for this_line in p_files["p-tld-ns"]:
	if this_line == "        - us. 172800 IN NS c.cctld.us.\n":
		continue
	else:
		out_text += this_line
n_files["n-vnk-gut"] = out_text

# Add a new record to Additional
out_text = "# [rse] Start with p-tld-ns, add an A for c.cctld.us\n"
for this_line in p_files["p-tld-ns"]:
	if this_line == "        - c.cctld.us. 172800 IN A 156.154.127.70\n":
		out_text += "        - c.cctld.us. 172800 IN A 156.154.127.99\n"
	out_text += this_line
n_files["n-vnk-rse"] = out_text

# Change a record in Additional
out_text = "# [ykm] Start with p-tld-ns, change A for c.cctld.us\n"
for this_line in p_files["p-tld-ns"]:
	if this_line == "        - c.cctld.us. 172800 IN A 156.154.127.70\n":
		out_text = "        - c.cctld.us. 172800 IN A 156.154.127.99\n"
	else:
		out_text += this_line
n_files["n-vnk-ykm"] = out_text

# Delete a a record from Additional
out_text = "# [xpa] Start with p-tld-ns, change A for c.cctld.us\n"
for this_line in p_files["p-tld-ns"]:
	if this_line == "        - c.cctld.us. 172800 IN A 156.154.127.70\n":
		continue
	else:
		out_text += this_line
n_files["n-vnk-xpa"] = out_text

################## When done with all that 

# Create the n files
for this_file_name in n_files:
	f = open(this_file_name, mode="wt")
	f.write(n_files[this_file_name])
	f.close()
