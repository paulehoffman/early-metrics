#!/usr/bin/env python3
''' Program to make tests for metrics testing '''

# Text is copied from rssac-047.mkd

# Read all the positive files into memory
p_file_names = '''
p-dot-dnskey
p-dot-ns
p-dot-soa
p-neg
p-tld-ds
p-tld-ns
'''.strip().splitlines()

p_files = {}
for this_file in p_file_names:
	p_files[this_file] = open(this_file, mode="rt").read().splitlines()

def create_n_file(id, compare_name, desc, file_lines):
	compare_lines = p_files[compare_name]
	# Check if nothing changed
	if file_lines == compare_lines:
		exit("Found unchanged test creation for {}".format(id))
	# Check if the test does not start as expected
	if not file_lines[0] == "-":
		exit("First line of {} was not '-'".format(id))
	# Write the file
	f = open("n-{}".format(id), mode="wt")
	f.write("# [{}] {}".format(id, desc))
	for this_line in file_lines:
		f.write(this_line + "\n")
	f.close()

# All of the RRsets in the Answer, Authority, and Additional sections match RRsets found in the zone. [vnk]

# Add a new record to Answer
id = "ffr"
compare_name = "p-dot-ns"
desc = "Start with p-dot-ns, add z.root-servers.net to Answer\n"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.":
		file_lines.append("        - . 518400 IN NS z.root-servers.net.")
	file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Change a record in Answer
id = "vpn"
compare_name = "p-dot-ns"
desc = "Start with p-dot-ns, change a.root-server.net to z.root-servers.net in Answer\n"
for this_line in p_files[compare_name]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.":
		file_lines.append("        - . 518400 IN NS z.root-servers.net.")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Delete a record from Answer
id = "uuc"
compare_name = "p-dot-ns"
desc = "Start with p-dot-ns, delete a.root-servers.net from Answer\n"
for this_line in p_files[compare_name]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.":
		continue
	file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

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
		out_text += "        - us. 172800 IN NS z.cctld.us.\n"
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
		out_text += "        - c.cctld.us. 172800 IN A 156.154.127.99\n"
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

