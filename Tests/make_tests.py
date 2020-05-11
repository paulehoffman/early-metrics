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
p-tld-ns-no-ds
'''.strip().splitlines()

p_files = {}
for this_file in p_file_names:
	p_files[this_file] = open(this_file, mode="rt").read().splitlines()

##########

# Whenever possible, create test cases that do not also cause validation failures

##########

# All of the RRsets in the Answer, Authority, and Additional sections match RRsets found in the zone. [vnk]
#   Add and change records in Answer (although this will always fail due to DNSSEC validation)
#   Add and change unsigned records in Authority
#   Add and change unsigned records in Addtional
#   Note that deleting records is not covered here because that can't be tested

# Add a new record to Answer
id = "ffr"
compare_name = "p-dot-ns"
desc = "Start with p-dot-ns, add z.root-servers.net to Answer; will have DNSSEC validation failure"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.":
		file_lines.append("        - . 518400 IN NS z.root-servers.net.")
	file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Change a record in Answer
id = "vpn"
compare_name = "p-dot-ns"
desc = "Start with p-dot-ns, change a.root-server.net to z.root-servers.net in Answer; will have DNSSEC validation failure"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.":
		file_lines.append("        - . 518400 IN NS z.root-servers.net.")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Add a new record to Authority 
id = "zoc"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, add z.cctld.us to Authority; use NS because it is unsigned"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - us. 172800 IN NS c.cctld.us.":
		file_lines.append("        - us. 172800 IN NS z.cctld.us.")
	file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Change a record in Authority
id = "gye"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, change c.cctld.us to z.cctld.us in Authority; use NS because it is unsigned"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - us. 172800 IN NS c.cctld.us.":
		file_lines.append("        - us. 172800 IN NS z.cctld.us.")
	else:
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

##########

# All RRsets that are signed have their signatures validated. [yds]
#   Change the RRSIGs in different ways
#   p-tld-ds has signed DS records for .us in the answer; the RRSIG looks like:
#           - us. 86400 IN RRSIG DS 8 1 86400 20200513170000 20200430160000 48903 . iwAdFM7FNufqTpU/pe1nySyTeND3C2KvzXgMYR3+yLMXhu1bqbQ+Dy7G . . .

# Change the RDATA
id = "uuc"
compare_name = "p-tld-ds"
desc = "Start with p-tld-ds, change the RRSIG RData in the Answer; causes validation failure"
file_lines = []
for this_line in p_files[compare_name]:
	if "RRSIG DS 8 1 86400 20200513170000 20200430160000" in this_line:
		file_lines.append(this_line.replace("RRSIG DS 8", "RRSIG AAAA 8"))
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Change the signature value itself
id = "gut"
compare_name = "p-tld-ds"
desc = "Start with p-tld-ds, change the RRSIG signature; causes validation failure"
file_lines = []
for this_line in p_files[compare_name]:
	if "RRSIG DS 8 1 86400 20200513170000 20200430160000" in this_line:
		file_lines.append(this_line.replace("pe1nySyTeND3C2KvzXgMYR3", "pe1nySyTeND3C2KvzXgMYR4"))
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

##########

# For positive responses with QNAME = <TLD> and QTYPE = NS, a correct result requires all of the following: [hmk]
#   Use p-tld-ns

# The header AA bit is not set. [ujy]
id = "xpa"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, set the AA bit"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "      flags: qr":
		file_lines.append("      flags: qr aa")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Answer section is empty. [aeg]
id = "aul"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, create a bogus Answer section with the NS records" 
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "      AUTHORITY_SECTION:":
		file_lines.append("      ANSWER_SECTION:")
		file_lines.append("        - us. 172800 IN NS c.cctld.us.")
		file_lines.append("        - us. 172800 IN NS k.cctld.us.")
		file_lines.append("        - us. 172800 IN NS a.cctld.us.")
		file_lines.append("        - us. 172800 IN NS b.cctld.us.")
		file_lines.append("        - us. 172800 IN NS f.cctld.us.")
		file_lines.append("        - us. 172800 IN NS e.cctld.us.")
		file_lines.append("      AUTHORITY_SECTION:")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Authority section contains the entire NS RRset for the query name. [pdd]
id = "mbh"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, remove NS k.cctld.us. from the Authority section" 
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - us. 172800 IN NS k.cctld.us.":
		continue
	file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# If the DS RRset for the query name exists in the zone: [hue]
#   The Authority section contains the signed DS RRset for the query name. [kbd]
id = "csl"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, remove one of the DS records from the Authority section; will cause validation failure" 
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - us. 86400 IN DS 39361 8 1 09E0AF18E54225F87A3B10E95C9DA3F1E58E5B59":
		continue
	file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# If the DS RRset for the query name does not exist in the zone: [fot]
#   The Authority section contains no DS RRset. [bgr]
#   The Authority section contains a signed NSEC RRset covering the query name. [mkl]
id = "jke"
compare_name = "p-tld-ns-no-ds"
desc = "Start with p-tld-ns-no-ds, add a DS records to the Authority section" 
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "      AUTHORITY_SECTION:":
		file_lines.append(this_line)
		file_lines.append("        - cm. 86400 IN DS 39361 8 1 09E0AF18E54225F87A3B10E95C9DA3F1E58E5B59")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

id = "gpn"
compare_name = "p-tld-ns-no-ds"
desc = "Start with p-tld-ns-no-ds, remove the NSEC and its signature" 
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - cm. 86400 IN NSEC cn. NS RRSIG NSEC":
		continue
	if this_line.startswith("        - cm. 86400 IN RRSIG NSEC"):
		continue
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Additional section contains at least one A or AAAA record found in the zone associated with at least one NS record found in the Authority section. [cjm]
id = "fvg"
compare_name = "p-tld-ns"
desc = "Start with p-tld-ns, remove all the glue records and add a fake one" 
file_lines = []
for this_line in p_files[compare_name]:
	if "cctld.us. 172800 IN" in this_line:
		file_lines.append("        - z.cctld.us. 172800 IN A 156.154.127.70")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

##########

# For positive responses where QNAME = <TLD> and QTYPE = DS, a correct result requires all of the following: [dru]
#   Use p-tld-ds

# The header AA bit is set. [yot]
id = "ttr"
compare_name = "p-tld-ds"
desc = "Start with p-tld-ds, remove the AA bit"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "      flags: qr aa":
		file_lines.append("      flags: qr")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Answer section contains the signed DS RRset for the query name. [cpf]
id = "zjs"
compare_name = "p-tld-ds"
desc = "Start with p-tld-ds, remove the the first DS record; validation will fail"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - us. 86400 IN DS 39361 8 1 09E0AF18E54225F87A3B10E95C9DA3F1E58E5B59":
		continue
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Authority section is empty. [xdu]
id = "rpr"
compare_name = "p-tld-ds"
desc = "Start with p-tld-ds, add an Authority section with an NS record"
file_lines = []
for this_line in p_files[compare_name]:
	if "us. 86400 IN RRSIG" in this_line:
		file_lines.append(this_line)
		file_lines.append("      AUTHORITY_SECTION:")
		file_lines.append("        - us. 172800 IN NS c.cctld.us.")
create_n_file(id, compare_name, desc, file_lines) 
      
# The Additional section is empty. [mle]
id = "ekf"
compare_name = "p-tld-ds"
desc = "Start with p-tld-ds, add an Additonal section with an A record"
file_lines = []
for this_line in p_files[compare_name]:
	if "us. 86400 IN RRSIG" in this_line:
		file_lines.append(this_line)
		file_lines.append("      ADDITIONAL_SECTION:")
		file_lines.append("        - c.cctld.us. 172800 IN A 156.154.127.70")
create_n_file(id, compare_name, desc, file_lines) 

# For positive responses for QNAME = . and QTYPE = SOA, a correct result requires all of the following: [owf]
#   Use p-dot-soa

# The header AA bit is set. [xhr]
id = "apf"
compare_name = "p-dot-soa"
desc = "Start with p-dot-soa, remove the AA bit"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "      flags: qr aa":
		file_lines.append("      flags: qr")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Answer section contains the signed SOA record for the root. [obw]
id = "apf"
compare_name = "p-dot-soa"
desc = "Start with p-dot-soa, remove the Answer section"
file_lines = []
for this_line in p_files[compare_name]:
	if "ANSWER_SECTION:" in this_line:
		continue
	if ". 86400 IN SOA" in this_line:
		continue
	if ". 86400 IN RRSIG SOA" in this_line:
		continue
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Authority section contains the signed NS RRset for the root. [ktm]
id = "mtg"
compare_name = "p-dot-soa"
desc = "Start with p-dot-soa, remove a.root-servers.net from the Authority section"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.":
		continue
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

##########

