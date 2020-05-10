#!/usr/bin/env python3
''' Program to make tests for metrics testing '''
import glob, os

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
	f.write("# [{}] {}\n".format(id, desc))
	for this_line in file_lines:
		f.write(this_line + "\n")
	f.close()

# Delete all the negative files before re-creating them
for this_to_delete in glob.glob("n-*"):
	try:
		os.unlink(this_to_delete)
	except:
		exit("Stopping early because can't delete {}".format(this_to_delete))

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

##########

# All of the RRsets in the Answer, Authority, and Additional sections match RRsets found in the zone. [vnk]

# Add a new record to Answer
id = "ffr"
compare_name = "p-dot-ns"
desc = "Start with p-dot-ns, add z.root-servers.net to Answer"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.":
		file_lines.append("        - . 518400 IN NS z.root-servers.net.")
	file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Change a record in Answer
id = "vpn"
compare_name = "p-dot-ns"
desc = "Start with p-dot-ns, change a.root-server.net to z.root-servers.net in Answer"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.":
		file_lines.append("        - . 518400 IN NS z.root-servers.net.")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Delete a record from Answer
id = "uuc"
compare_name = "p-dot-ns"
desc = "Start with p-dot-ns, delete a.root-servers.net from Answer"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.":
		continue
	file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Add a new record to Authority 
id = "zoc"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, add z.cctld.us from Authority"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - us. 172800 IN NS c.cctld.us.":
		file_lines.append("        - us. 172800 IN NS z.cctld.us.")
	file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Change a record in Authority
id = "gye"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, change z.cctld.us to z.cctld.us in Authority"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - us. 172800 IN NS c.cctld.us.":
		file_lines.append("        - us. 172800 IN NS z.cctld.us.")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Delete a a record from Authority
id = "gut"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, delete c.cctld.us.in Authority"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - us. 172800 IN NS c.cctld.us.":
		continue
	file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Add a new record to Additional
id = "rse"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, add an A for c.cctld.us in Additional"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - c.cctld.us. 172800 IN A 156.154.127.70":
		file_lines.append("        - c.cctld.us. 172800 IN A 156.154.127.99")
	file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Change a record in Additional
id = "ykm"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, change A for c.cctld.us in Addtional"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - c.cctld.us. 172800 IN A 156.154.127.70":
		file_lines.append("        - c.cctld.us. 172800 IN A 156.154.127.99")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Delete a a record from Additional
id = "xpa"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, change A for c.cctld.us.in Additional"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - us. 172800 IN NS c.cctld.us.":
		continue
	file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

##########

