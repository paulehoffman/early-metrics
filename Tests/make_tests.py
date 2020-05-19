#!/usr/bin/env python3
''' Program to make tests for metrics testing '''
import glob, os, subprocess

def create_n_file(id, compare_name, desc, file_lines):
	if id in all_n_ids:
		exit("Found {} a second time. Exiting.".format(id))
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
	all_n_ids.append(id)

# Template for . SOA
#    dig +yaml . SOA @a.root-servers.net -4 +notcp +nodnssec +noauthority +noadditional +bufsize=1220 +nsid +norecurse +time=4 +tries=1
# Template for all other digs
#    dig +yaml {} {} @a.root-servers.net -4 +notcp +dnssec +bufsize=1220 +nsid +norecurse +time=4 +tries=1 +noignore

dig_loc = os.path.expanduser("~/Target/bin/dig")
p_template = "@a.root-servers.net -4 +notcp +dnssec +bufsize=1220 +nsid +norecurse +time=4 +tries=1 +noignore"

# Create the positive files
cmd_list = """
{} +yaml . SOA {} > p-dot-soa
{} +yaml . DNSKEY {} > p-dot-dnskey
{} +yaml . NS {} > p-dot-ns
{} +yaml www.rssac047-test.abcdefghij A {} > p-neg
{} +yaml us DS {} > p-tld-ds
{} +yaml us NS {} > p-tld-ns
{} +yaml cm NS {} > p-tld-ns-no-ds
{} +yaml by NS {} > p-by-ns
""".strip().splitlines()

for this_cmd in cmd_list:
	subprocess.run(this_cmd.format(dig_loc, p_template), shell=True)

# Fix p-by-ns for the BIND YAML bug
all_by_lines = []
for this_line in open("p-by-ns", mode="rt"):
	if this_line.endswith("::\n"):
		this_line = this_line.replace("::\n", "::0\n")
	all_by_lines.append(this_line)
f = open("p-by-ns", mode="wt")
f.write("".join(all_by_lines))
f.close()

# Delete all the negative files before re-creating them
for this_to_delete in glob.glob("n-*"):
	try:
		os.unlink(this_to_delete)
	except:
		exit("Stopping early because can't delete {}".format(this_to_delete))

# Read all the positive files into memory
p_file_names = '''
p-dot-soa
p-dot-dnskey
p-dot-ns
p-neg
p-tld-ds
p-tld-ns
p-tld-ns-no-ds
p-by-ns
'''.strip().splitlines()

p_files = {}
for this_file in p_file_names:
	p_files[this_file] = open(this_file, mode="rt").read().splitlines()

# Keep track of the IDs to make sure we don't accidentally copy one
all_n_ids = []

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
compare_name = "p-dot-dnskey"
desc = "Start with p-dot-dnskey, change the RRSIG RData in the Answer; causes validation failure"
file_lines = []
for this_line in p_files[compare_name]:
	if "AwEAAaz/tAm8yTn4Mfeh" in this_line:
		file_lines.append(this_line.replace("AwEAAaz/tAm8yTn4Mfeh", "AwEAAaz/tAm8yTn4MfeH"))
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# Change the signature value itself
id = "gut"
compare_name = "p-dot-dnskey"
desc = "Start with p-dot-dnskey, change the RRSIG signature; causes validation failure"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line.startswith("        - . 172800 IN RRSIG DNSKEY"):
		file_lines.append(this_line.replace("Q", "q"))
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
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 
      
# The Additional section is empty. [mle]
id = "ekf"
compare_name = "p-tld-ds"
desc = "Start with p-tld-ds, add an Additonal section with an A record"
file_lines = []
for this_line in p_files[compare_name]:
		file_lines.append(this_line)
file_lines.append("      ADDITIONAL_SECTION:")
file_lines.append("        - c.cctld.us. 172800 IN A 156.154.127.70")
create_n_file(id, compare_name, desc, file_lines) 

##########

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
id = "jjg"
compare_name = "p-dot-soa"
desc = "Start with p-dot-soa, remove the SOA from Answer section; this will fail validation"
file_lines = []
for this_line in p_files[compare_name]:
	if ". 86400 IN SOA" in this_line:
		continue
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Authority section contains the signed NS RRset for the root. [ktm]
id = "mtg"
compare_name = "p-dot-soa"
desc = "Start with p-dot-soa, remove a.root-servers.net from the Authority section; this will fail validation"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.":
		continue
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

##########

# For positive responses for QNAME = . and QTYPE = NS, a correct result requires all of the following: [amj]
#   Use p-dot-ns

# The header AA bit is set. [csz]
id = "kuc"
compare_name = "p-dot-ns"
desc = "Start with p-dot-ns, remove the AA bit"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "      flags: qr aa":
		file_lines.append("      flags: qr")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Answer section contains the signed NS RRset for the root. [wal]
id = "oon"
compare_name = "p-dot-ns"
desc = "Start with p-dot-ns, remove a.root-servers.net. from the Answer section; this will fail validation"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "        - . 518400 IN NS a.root-servers.net.":
		continue
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Authority section is empty. [eyk]
id = "hmp"
compare_name = "p-dot-ns"
desc = "Start with p-dot-ns, add an Authority section with an A record for a.root-servers.net."
file_lines = []
for this_line in p_files[compare_name]:
	file_lines.append(this_line)
file_lines.append("      AUTHORITY_SECTION:")
file_lines.append("        - a.root-servers.net. 518400 IN A 198.41.0.4")
create_n_file(id, compare_name, desc, file_lines)

##########

# For positive responses for QNAME = . and QTYPE = DNSKEY, a correct result requires all of the following: [djd]
#   Use p-dot-dnskey

# The header AA bit is set. [occ]
id = "kbc"
compare_name = "p-dot-dnskey"
desc = "Start with p-dot-dnskey, remove the AA bit"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "      flags: qr aa":
		file_lines.append("      flags: qr")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Answer section contains the signed DNSKEY RRset for the root. [eou]
id = "nsz"
compare_name = "p-dot-dnskey"
desc = "Start with p-dot-dnskey, remove the DNSKEY that contains 'AwEAAc4qsciJ5MdMU'; this will fail validation "
file_lines = []
for this_line in p_files[compare_name]:
	if "AwEAAc4qsciJ5MdMU" in this_line:
		continue
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Authority section is empty. [kka]
id = "coh"
compare_name = "p-dot-dnskey"
desc = "Start with p-dot-dnskey, add an Authority section with an NS record for a.root-servers.net."
file_lines = []
for this_line in p_files[compare_name]:
	file_lines.append(this_line)
file_lines.append("      AUTHORITY_SECTION:")
file_lines.append("        - . 518400 IN NS a.root-servers.net.")
create_n_file(id, compare_name, desc, file_lines)

# The Additional section is empty. [jws]
id = "nnd"
compare_name = "p-dot-dnskey"
desc = "Start with p-dot-dnskey, add an Additional section with an A record for a.root-servers.net."
file_lines = []
for this_line in p_files[compare_name]:
	file_lines.append(this_line)
file_lines.append("      ADDITIONAL_SECTION:")
file_lines.append("        - a.root-servers.net. 518400 IN A 198.41.0.4")
create_n_file(id, compare_name, desc, file_lines)

##########

# For negative responses, a correct result requires all of the following: [vcu]
#   Use p-neg

# The header AA bit is set. [gpl]
id = "ymb"
compare_name = "p-neg"
desc = "Start with p-neg, remove the AA bit"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "      flags: qr aa":
		file_lines.append("      flags: qr")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Answer section is empty. [dvh]
id = "njw"
compare_name = "p-neg"
desc = "Start with p-neg, , create a bogus Answer section with an A record"
file_lines = []
for this_line in p_files[compare_name]:
	if this_line == "      AUTHORITY_SECTION:":
		file_lines.append("      ANSWER_SECTION:")
		file_lines.append("        - www.rssac047-test.hwzvpicwen. 518400 IN A 127.0.0.1")
		file_lines.append("      AUTHORITY_SECTION:")
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Authority section contains the signed . / SOA record. [axj]
id = "pho"
compare_name = "p-neg"
desc = "Start with p-neg, , remove the SOA record and its RRSIG"
file_lines = []
for this_line in p_files[compare_name]:
	if ". 86400 IN SOA" in this_line:
		continue
	if ". 86400 IN RRSIG SOA" in this_line:
		continue
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Authority section contains a signed NSEC record covering the query name. [czb]
id = "czg"
compare_name = "p-neg"
desc = "Start with p-neg, , remove the NSEC record covering the query and its RRSIG"
file_lines = []
for this_line in p_files[compare_name]:
	if "abc. 86400 IN NSEC" in this_line:
		continue
	if "abc. 86400 IN RRSIG NSEC" in this_line:
		continue
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Authority section contains a signed NSEC record with owner name “.” proving no wildcard exists in the zone. [jhz]
id = "pdu"
compare_name = "p-neg"
desc = "Start with p-neg, , remove the NSEC record covering the . and its RRSIG"
file_lines = []
for this_line in p_files[compare_name]:
	if ". 86400 IN NSEC aaa." in this_line:
		continue
	if ". 86400 IN RRSIG NSEC" in this_line:
		continue
	else:
		file_lines.append(this_line)
create_n_file(id, compare_name, desc, file_lines) 

# The Additional section is empty. [trw]
id = "anj"
compare_name = "p-neg"
desc = "Start with p-neg,add an Additonal section with an A record"
file_lines = []
for this_line in p_files[compare_name]:
	file_lines.append(this_line)
file_lines.append("      ADDITIONAL_SECTION:")
file_lines.append("        - c.cctld.us. 172800 IN A 156.154.127.70")
create_n_file(id, compare_name, desc, file_lines) 

##########

# Read the p-dot-soa and write out the SOA to soa-to-use
the_soa = ""
for this_line in open("p-dot-soa", mode="rt"):
	if "- . 86400 IN SOA a.root-servers.net. nstld.verisign-grs.com" in this_line:
		parts = this_line.strip().split(" ")
		the_soa = parts[7]
if not the_soa:
	exit("Didn't find an SOA. Exiting.")
print("Found SOA {}".format(the_soa))
f = open("soa-to-use", mode="wt")
f.write("{}\n".format(the_soa))
f.close()
exit("Created {} files for the negative tests".format(len(all_n_ids)))
