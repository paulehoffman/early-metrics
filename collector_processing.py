#!/usr/bin/env python3

''' Do all tasks on the collector to get data from the VPs, process it, and put the results in the database tables '''
# Run as the metrics user
# Three-letter items in square brackets (such as [xyz]) refer to parts of rssac-047.md

import datetime, glob, gzip, logging, os, pickle, psycopg2, re, requests, subprocess, shutil, yaml
from concurrent import futures

def get_files_from_one_vp(this_vp):
	# Used to pull files from VPs under multiprocessing; retuns the number of files pulled from this VP
	pulled_count = 0
	# Make a batch file for sftp that gets the directory
	dir_batch_filename = "{}/dirbatchfile.txt".format(log_dir)
	dir_f = open(dir_batch_filename, mode="wt")
	dir_f.write("cd transfer/Output\ndir -1\n")
	dir_f.close()
	# Execuite sftp with the directory batch file
	try:
		p = subprocess.run("sftp -b {} transfer@{}".format(dir_batch_filename, this_vp), shell=True, capture_output=True, text=True, check=True)
	except Exception as e:
		alert("Getting directory for {} ended with '{}'".format(dir_batch_filename, e))
	dir_lines = p.stdout.splitlines()
	# Get the filenames that end in .gz; some lines will be other cruft such as ">"
	for this_filename in dir_lines:
		if not this_filename.endswith(".gz"):
			continue
		# Create an sftp batch file for each file to get
		get_batch_filename = "{}/getbatchfile.txt".format(log_dir)
		get_f = open(get_batch_filename, mode="wt")
		# Get the file
		get_cmd = "get transfer/Output/{} {}\n".format(this_filename, incoming_dir)
		get_f.write(get_cmd)
		get_f.close()
		try:
			p = subprocess.run("sftp -b {} transfer@{}".format(get_batch_filename, this_vp), shell=True, capture_output=True, text=True, check=True)
		except Exception as e:
			die("Running get for {} ended with '{}'".format(this_filename, e))
		# Create an sftp batch file for each file to move
		move_batch_filename = "{}/getbatchfile.txt".format(log_dir)
		move_f = open(move_batch_filename, mode="wt")
		# Get the file
		move_cmd = "rename transfer/Output/{0} transfer/AlreadySeen/{0}\n".format(this_filename)
		move_f.write(move_cmd)
		move_f.close()
		try:
			p = subprocess.run("sftp -b {} transfer@{}".format(move_batch_filename, this_vp), shell=True, capture_output=True, text=True, check=True)
		except Exception as e:
			die("Running rename for {} ended with '{}'".format(this_filename, e))
		pulled_count += 1
		try:
			conn = psycopg2.connect(dbname="metrics", user="metrics")
			cur = conn.cursor()
			cur.execute("insert into files_gotten (filename_full, retrieved_at) values (%s, %s);", (this_filename, datetime.datetime.now(datetime.timezone.utc)))
			conn.commit()
			cur.close()
			conn.close()
		except Exception as e:
			die("Could not insert '{}' into files_gotten: '{}'".format(this_filename, e))
	return pulled_count

###############################################################
	
def process_one_incoming_file(full_file):
	# Process an incoming file, and move it when done
	#   Returns nothing
	#   File-level errors cause "die", record-level errors cause "alert" and skipping the record
	try:
		conn = psycopg2.connect(dbname="metrics", user="metrics")
		cur = conn.cursor()
		conn.set_session(autocommit=True)
	except Exception as e:
		die("Could not open database in process_one_incoming_file: {}".format(e))
	# Check for bad file
	if not full_file.endswith(".pickle.gz"):
		alert("Found {} that did not end in .pickle.gz".format(full_file))
		return
	short_file = os.path.basename(full_file).replace(".pickle.gz", "")
	# Ungz it
	try:
		with gzip.open(full_file, mode="rb") as pf:
			in_pickle = pf.read()
	except Exception as e:
		die("Could not unzip {}: '{}'".format(full_file, e))
	# Unpickle it
	try:
		in_obj = pickle.loads(in_pickle)
	except Exception as e:
		die("Could not unpickle {}: '{}'".format(full_file, e))
	# Sanity check the record
	if not ("d" in in_obj) and ("e" in in_obj) and ("r" in in_obj) and ("s" in in_obj) and ("v" in in_obj):
		alert("Object in {} did not contain keys d, e, r, s, and v".format(full_file))

	# Move the file to ~/Originals/yyyymm so it doesn't get processed again
	year_from_short_file = short_file[0:4]
	month_from_short_file = short_file[4:6]
	original_dir_target = os.path.expanduser("~/Originals/{}{}".format(year_from_short_file, month_from_short_file))
	if not os.path.exists(original_dir_target):
		try:
			os.mkdir(original_dir_target)
		except Exception as e:
			die("Could not create {}: '{}'".format(original_dir_target, e))
	try:
		shutil.move(full_file, original_dir_target)
	except Exception as e:
			die("Could not move {} to {}: '{}'".format(full_file, original_dir_target, e))

	# Log the metadata
	update_string = "update files_gotten set processed_at=%s, version=%s, delay=%s, elapsed=%s where filename_full=%s"
	update_vales = (datetime.datetime.now(datetime.timezone.utc), in_obj["v"], in_obj["d"], in_obj["e"], short_file+".pickle.gz") 
	try:
		cur.execute(update_string, update_vales)
	except Exception as e:
		alert("Could not update {} in files_gotten: '{}'".format(short_file, e))

	# Get the derived date and VP name from the file name
	(file_date_text, file_vp) = short_file.split("-")
	try:
		file_date = datetime.datetime(int(file_date_text[0:4]), int(file_date_text[4:6]), int(file_date_text[6:8]),\
			int(file_date_text[8:10]), int(file_date_text[10:12]))
	except Exception as e:
		die("Could not split the file name '{}' into a datetime: '{}'".format(short_file, e))

	# Log the route information from in_obj["s"]
	if not in_obj.get("s"):
		alert("File {} did not have a route information record".format(full_file))
	else:
		update_string = "insert into route_info (file_prefix, date_derived, vp, route_string) values (%s, %s, %s, %s)"
		update_vales = (short_file, file_date, file_vp, in_obj["s"]) 
		try:
			cur.execute(update_string, update_vales)
		except Exception as e:
			alert("Could not insert into route_info for {}: '{}'".format(short_file, e))

	# Walk through the response items from the unpickled file
	response_count = 0
	for this_resp in in_obj["r"]:
		response_count += 1
		# Get it out of YAML and do basic sanity checks
		try:
			this_resp_obj = yaml.load(this_resp[6])
		except:
			alert("Could not interpret YAML from {} of {}".format(response_count, full_file))
			continue
		# Sanity check the structure of the object
		if not this_resp_obj:
			alert("Found no object in record {} of {}".format(response_count, full_file))
			continue
		if not this_resp_obj[0].get("type"):
			alert("Found no dig type in record {} of {}".format(response_count, full_file))
			continue
		if not this_resp_obj[0].get("message"):
			alert("Found no message in record {} of {}".format(response_count, full_file))
			continue
		# Each record is "S" for an SOA record or "C" for a correctness test
		if this_resp[4] == "S":
			# Get the this_dig_elapsed, this_timeout, this_soa for the response
			if this_resp_obj[0]["type"] == "MESSAGE":
				if (not this_resp_obj[0]["message"].get("response_time")) or (not this_resp_obj[0]["message"].get("query_time")):
					alert("Found a message without response_time or query_time in record {} of {}".format(response_count, full_file))
					continue
				dig_elapsed_as_delta = this_resp_obj[0]["message"]["response_time"] - this_resp_obj[0]["message"]["query_time"]
				this_dig_elapsed = datetime.timedelta.total_seconds(dig_elapsed_as_delta)
				this_timeout = False
				if not this_resp_obj[0]["message"].get("response_message_data").get("ANSWER_SECTION"):
					alert("Found a message without an answer in record {} of {}".format(response_count, full_file))
					continue
				this_soa_record = this_resp_obj[0]["message"]["response_message_data"]["ANSWER_SECTION"][0]
				soa_record_parts = this_soa_record.split(" ")
				this_soa = soa_record_parts[6]
			elif this_resp_obj[0]["type"] == "DIG_ERROR":
				if not (("timed out" in this_resp_obj[0]["message"]) or ("communications error" in this_resp_obj[0]["message"])):
					alert("Found unexpected dig error message '{}' in record {} of {}".format(this_resp_obj[0]["message"], response_count, full_file))
					continue
				this_dig_elapsed = None
				this_timeout = True
				this_soa = None
			else:
				alert("Found an unexpected dig type {} in record {} of {}".format(this_resp_obj[0]["type"], response_count, full_file))
				continue
			# Log the SOA information
			update_string = "insert into soa_info (file_prefix, date_derived, vp, rsi, internet, transport, prog_elapsed, dig_elapsed, timeout, soa) "\
				+ "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
			update_vales = (short_file, file_date, file_vp, this_resp[0], this_resp[1], this_resp[2], this_resp[5], this_dig_elapsed, this_timeout, this_soa) 
			try:
				cur.execute(update_string, update_vales)
			except Exception as e:
				alert("Could not insert into soa_info for {}: '{}'".format(short_file, e))
		elif this_resp[4] == "C": # Records for correctness checking
			# Here, we are writing the record out with None for the is_correct value; the correctness is check is done later in this pass
			update_string = "insert into correctness_info (file_prefix, date_derived, vp, rsi, internet, transport, recent_soa, "\
				+ " is_correct, failure_reason, source_pickle) "\
				+ "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
			# Set is_correct to NULL because it will be evaluated later
			update_vales = (short_file, file_date, file_vp, this_resp[0], this_resp[1], this_resp[2], [ this_soa ], None, None, pickle.dumps(this_resp_obj))
			try:
				cur.execute(update_string, update_vales)
			except Exception as e:
				alert("Could not insert into correctness_info for {}: '{}'".format(short_file, e))
		else:
			alert("Found a response type {}, which is not S or C, in record {} of {}".format(this_resp[4], response_count, full_file))
			continue
	cur.close()
	conn.close()
	return

###############################################################

def check_for_signed_rr(list_of_records_from_section, name_of_rrtype):
	# Part of correctness checking
	#   See if there is a record in the list of the given RRtype, and make sure there is also an RRSIG for that RRtype
	found_rrtype = False
	for this_full_record in list_of_records_from_section:
		(rec_qname, _, _, rec_qtype, rec_rdata) = this_full_record.split(" ", maxsplit=4)
		if rec_qtype == name_of_rrtype:
			found_rrtype = True
			break
	if not found_rrtype:
		return "No record of type {} was found in that section".format(name_of_rrtype)
	found_rrsig = False
	for this_full_record in list_of_records_from_section:
		(rec_qname, _, _, rec_qtype, rec_rdata) = this_full_record.split(" ", maxsplit=4)
		if rec_qtype == "RRSIG":
			found_rrsig = True
			break
	if not found_rrsig:
		return "One more more records of type {} were found in that section, but there was no RRSIG".format(name_of_rrtype)
	return ""
	
###############################################################

def process_one_correctness_tuple(in_tuple):
	# Process one tuple of id / SOA / pickle_of_response
	#   Returns nothing
	(this_id, this_recent_soa_serial_array, this_resp_pickle) = in_tuple
	try:
		conn = psycopg2.connect(dbname="metrics", user="metrics")
		cur = conn.cursor()
		conn.set_session(autocommit=True)
	except Exception as e:
		die("Could not open database in process_one_correctness_tuple: {}".format(e))
	# See if it is a timeout; if so, set is_correct but move on [lbl]
	try:
		this_resp_obj = pickle.loads(this_resp_pickle)
	except Exception as e:
		alert("Could not unpickle in correctness_info for {}: '{}'".format(this_id, e))
		return
	if this_resp_obj[0]["type"] == "DIG_ERROR":
		try:
			cur.execute("update correctness_info set (is_correct, failure_reason) = (%s, %s) where id = %s", (True, "", this_id))
		except Exception as e:
			alert("Could not update correctness_info for timed-out {}: '{}'".format(this_id, e))
		return
	elif not this_resp_obj[0]["type"] == "MESSAGE":
		alert("Found an unexpected dig type '{}' in correctness_info for {}".format(this_resp_obj[0]["type"], this_id))
		return
	
	# Convert this_recent_soa_serial_array into root_to_check by reading the file and unpickling it
	recent_soa_pickle_filename = "{}/{}.matching.pickle".format(saved_matching_dir, this_recent_soa_serial_array[-1])
	try:
		soa_f = open(recent_soa_pickle_filename, mode="rb")
	except:
		alert("Found SOA {} in correctness checking for {} for which there was no file".format(this_id, this_recent_soa_serial_array[-1]))
		return
	try:
		root_to_check = pickle.load(soa_f)
	except:
		alert("Could not unpickle {} while processing {} for correctness".format(recent_soa_pickle_filename, this_id))
		return
	
	# Here if it is a dig MESSAGE type
	#   failure_reasons holds an expanding set of reasons
	#   It is checked at the end of testing, and all "" entries eliminted
	#   If it is empty, then all correctness tests passed
	failure_reasons = []
	resp = this_resp_obj[0]["message"]["response_message_data"]

	# Check that each of the RRsets in the Answer, Authority, and Additional sections match RRsets found in the zone [vnk]
	#   This check does not include any RRSIG RRsets that are not named in the matching tests below. [ygx]
	# This check does not include any OPT RRset found in the Additional section because "dig +yaml" does not put them in the Additional section [pvz]
	# After this check is done, we no longer need to check RRsets from the answer against the root zone
	for this_section_name in [ "ANSWER_SECTION", "AUTHORITY_SECTION", "ADDITIONAL_SECTION" ]:
		if resp.get(this_section_name):
			rrsets_for_checking = {}
			for this_full_record in resp[this_section_name]:
				(rec_qname, _, _, rec_qtype, rec_rdata) = this_full_record.split(" ", maxsplit=4)
				if not rec_qtype == "RRSIG":  # [ygx]
					this_key = "{}/{}".format(rec_qname, rec_qtype)
					if not this_key in rrsets_for_checking:
						rrsets_for_checking[this_key] = set()
					rrsets_for_checking[this_key].add(rec_rdata)
			for this_rrset_key in rrsets_for_checking:
				if not this_rrset_key in root_to_check:
					failure_reasons.append("{} was in {} in the response but not the root".format(this_rrset_key, this_section_name))
				else:
					if rrsets_for_checking[this_rrset_key] < root_to_check[this_rrset_key]:
						failure_reasons.append("RRset '{}' in response is shorter than '{}' in root zone".\
							format(rrsets_for_checking[this_rrset_key], root_to_check[this_rrset_key]))
					elif rrsets_for_checking[this_rrset_key] > root_to_check[this_rrset_key]:
						failure_reasons.append("RRset '{}' in response is longer than '{}' in root zone".\
							format(rrsets_for_checking[this_rrset_key], root_to_check[this_rrset_key]))

	# Check that each of the RRsets that are signed have their signatures validated. [yds]
	#   Send all the records in each section to the function that checks for validity
	answer_and_authority_recs = []
	for this_section_name in [ "ANSWER_SECTION", "AUTHORITY_SECTION", "ADDITIONAL_SECTION" ]:
		if resp.get(this_section_name):
			answer_and_authority_recs.extend(resp[this_section_name])
	##### Find RRsets that have associated RRSIGs
	##### For each, call out to program that validates
	#####   If something does not validate, failure_reasons.append("XXXX did not validate")
	
	# Check that all the parts of the resp structure are correct, based on the type of answer
	question_record = resp["QUESTION_SECTION"][0]
	(this_qname, _, this_qtype) = question_record.split(" ")
	if resp["status"] == "NOERROR":
		if (this_qname != ".") and (this_qtype == "NS"):  # Processing for TLD / NS [hmk]
			# The header AA bit is not set. [ujy]
			if "aa" in resp["flags"]:
				failure_reasons.append("AA bit was set")
			# The Answer section is empty. [aeg]
			if resp.get("ANSWER_SECTION"):
				failure_reasons.append("Answer section was not empty")
			# The Authority section contains the entire NS RRset for the query name. [pdd]
			if not resp.get("AUTHORITY_SECTION"):
				failure_reasons.append("Authority section was empty")
			root_ns_for_qname = root_to_check["{}/NS".format(this_qname)]
			auth_ns_for_qname = set()
			for this_rec in resp["AUTHORITY_SECTION"]:
				(rec_qname, _, _, rec_qtype, rec_rdata) = this_rec.split(" ", maxsplit=4)
				if rec_qtype == "NS":
					auth_ns_for_qname.add(rec_rdata)
			if not auth_ns_for_qname == root_ns_for_qname:
				failure_reasons.append("NS RRset in Authority was '{}', but NS from root was '{}'".format(auth_ns_for_qname, root_ns_for_qname))
			# If the DS RRset for the query name exists in the zone: [hue]
			if root_to_check.get("{}/DS".format(this_qname)):
				# The Authority section contains the signed DS RRset for the query name. [kbd]
				failure_reasons.append(check_for_signed_rr(resp["AUTHORITY_SECTION"], "DS"))
			else:  # If the DS RRset for the query name does not exist in the zone: [fot]
				# The Authority section contains no DS RRset. [bgr]
				for this_rec in resp["AUTHORITY_SECTION"]:
					(rec_qname, _, _, rec_qtype, _) = this_rec.split(" ", maxsplit=4)
					if rec_qtype == "DS":
						failure_reasons.append("Found DS in Authority section")
						break
				# The Authority section contains a signed NSEC RRset covering the query name. [mkl]
				has_covering_nsec = False
				for this_rec in resp["AUTHORITY_SECTION"]:
					(rec_qname, _, _, rec_qtype, rec_rdata) = this_rec.split(" ", maxsplit=4)
					if rec_qtype == "NSEC":
						if rec_qname == this_qname:
							has_covering_nsec = True
							break
				if not has_covering_nsec:
					failure_reasons.append("Authority section had no covering NSEC record")
			# Additional section contains at least one A or AAAA record found in the zone associated with at least one NS record found in the Authority section. [cjm]
			#    Collect the NS records from the Authority section
			found_NS_recs = []
			for this_rec in resp["AUTHORITY_SECTION"]:
				(rec_qname, _, _, rec_qtype, rec_rdata) = this_rec.split(" ", maxsplit=4)
				if rec_qtype == "NS":
					found_NS_recs.append(rec_rdata)
			found_qname_of_A_AAAA_recs = []
			for this_rec in resp["ADDITIONAL_SECTION"]:
				(rec_qname, _, _, rec_qtype, rec_rdata) = this_rec.split(" ", maxsplit=4)
				if rec_qtype in ("A", "AAAA"):
					found_qname_of_A_AAAA_recs.append(rec_qname)
			found_A_AAAA_NS_match = False
			for a_aaaa_qname in found_qname_of_A_AAAA_recs:
					if a_aaaa_qname in found_NS_recs:
						found_A_AAAA_NS_match = True
						break
			if not found_A_AAAA_NS_match:
				failure_reasons.append("No QNAMEs from A and AAAA in Additional {} matched NS from Authority {}".format(found_qname_of_A_AAAA_recs, found_NS_recs))
		elif (this_qname != ".") and (this_qtype == "DS"):  # Processing for TLD / DS [dru]
			# The header AA bit is set. [yot]
			if not "aa" in resp["flags"]:
				failure_reasons.append("AA bit was not set")
			# The Answer section contains the signed DS RRset for the query name. [cpf]
			if not resp.get("ANSWER_SECTION"):
				failure_reasons.append("Answer section was empty")
			else:
				# Make sure the DS is for the query name
				for this_rec in resp["ANSWER_SECTION"]:
					(rec_qname, _, _, rec_qtype, _) = this_rec.split(" ", maxsplit=4)
					if rec_qtype == "DS":
						if not rec_qname == this_qname:
							failure_reasons.append("DS in Answer section had QNAME {} instead of {}".format(rec_qname, this_qname))
				failure_reasons.append(check_for_signed_rr(resp["ANSWER_SECTION"], "DS"))
			# The Authority section is empty. [xdu]
			if resp.get("AUTHORITY_SECTION"):
				failure_reasons.append("Authority section was not empty")
			# The Additional section is empty. [mle]
			if resp.get("ADDITIONAL_SECTION"):
				failure_reasons.append("Additional section was not empty")
		elif (this_qname == ".") and (this_qtype == "SOA"):  # Processing for . / SOA
			# The header AA bit is set. [xhr]
			if not "aa" in resp["flags"]:
				failure_reasons.append("AA bit was not set")
			# The Answer section contains the signed SOA record for the root. [obw]
			failure_reasons.append(check_for_signed_rr(resp["ANSWER_SECTION"], "SOA"))
			# The Authority section contains the signed NS RRset for the root. [ktm]
			failure_reasons.append(check_for_signed_rr(resp["AUTHORITY_SECTION"], "NS"))
		elif (this_qname == ".") and (this_qtype == "NS"):  # Processing for . / NS [amj]
			# The header AA bit is set. [csz]
			if not "aa" in resp["flags"]:
				failure_reasons.append("AA bit was not set")
			# The Answer section contains the signed NS RRset for the root. [wal]
			failure_reasons.append(check_for_signed_rr(resp["ANSWER_SECTION"], "NS"))
			# The Authority section is empty. [eyk]
			if resp.get("AUTHORITY_SECTION"):
				failure_reasons.append("Authority section was not empty")
		elif (this_qname == ".") and (this_qtype == "DNSKEY"):  # Processing for . / DNSKEY [djd]
			# The header AA bit is set. [occ]
			if not "aa" in resp["flags"]:
				failure_reasons.append("AA bit was not set")
			# The Answer section contains the signed DNSKEY RRset for the root. [eou]
			failure_reasons.append(check_for_signed_rr(resp["ANSWER_SECTION"], "DNSKEY"))
			# The Authority section is empty. [kka]
			if resp.get("AUTHORITY_SECTION"):
				failure_reasons.append("Authority section was not empty")
			# The Additional section is empty. [jws]
			if resp.get("ADDITIONAL_SECTION"):
				failure_reasons.append("Additional section was not empty")
		else:
			failure_reasons.append("Not matched: when checking NOERROR statuses, found unexpected name/type of {}/{}".format(this_qname, this_qtype))
	elif resp["status"] == "NXDOMAIN":  # Processing for negative responses [vcu]
		# The header AA bit is set. [gpl]
		if not "aa" in resp["flags"]:
			failure_reasons.append("AA bit was not set")
		# The Answer section is empty. [dvh]
		if resp.get("ANSWER_SECTION"):
			failure_reasons.append("Answer section was not empty")
		# The Authority section contains the signed . / SOA record. [axj]
		if not resp.get("AUTHORITY_SECTION"):
			failure_reasons.append("Authority section was empty")
		else:
			# Make sure the SOA record is for .
			for this_rec in resp["AUTHORITY_SECTION"]:
				(rec_qname, _, _, rec_qtype, _) = this_rec.split(" ", maxsplit=4)
				if rec_qtype == "SOA":
					if not rec_qname == ".":
						failure_reasons.append("SOA in Authority section had QNAME {} instead of '.'".format(rec_qname))
			failure_reasons.append(check_for_signed_rr(resp["AUTHORITY_SECTION"], "SOA"))
			# The Authority section contains a signed NSEC record covering the query name. [czb]
			#   Note that the query name might have multiple labels, so only compare against the last
			this_qname_TLD = this_qname.split(".")[-2] + "."
			nsec_covers_query_name = False
			nsecs_in_authority = []
			for this_rec in resp["AUTHORITY_SECTION"]:
				(rec_qname, _, _, rec_qtype, rec_rdata) = this_rec.split(" ", maxsplit=4)
				if rec_qtype == "NSEC":
					nsec_parts = rec_rdata.split(" ")
					nsecs_in_authority.append("{}|{}".format(rec_qname, nsec_parts[0]))
					# Make a list of the three strings, then make sure the original QNAME is in the middle
					test_sort = sorted([rec_qname, nsec_parts[0], this_qname_TLD])
					if test_sort[1] == this_qname_TLD:
						nsec_covers_query_name = True
						break
			if not nsec_covers_query_name:
				failure_reasons.append("NSECs in Authority '{}' did not cover qname '{}'".format(nsecs_in_authority, this_qname))
			# The Authority section contains a signed NSEC record with owner name “.” proving no wildcard exists in the zone. [jhz]
			nsec_with_owner_dot = False
			for this_rec in resp["AUTHORITY_SECTION"]:
				(rec_qname, _, _, rec_qtype, rec_rdata) = this_rec.split(" ", maxsplit=4)
				if rec_qtype == "NSEC":
					if rec_qname == ".":
						nsec_with_owner_dot = True
						break;
			if not 	nsec_with_owner_dot:
				failure_reasons.append("Authority section did not contain a signed NSEC record with owner name '.'")
		# The Additional section is empty. [trw]
		if resp.get("ADDITIONAL_SECTION"):
			failure_reasons.append("Additional section was not empty")
	else:
		failure_reasons.append("Response had a status other than NOERROR and NXDOMAIN")
	
	# See if the results were all positive
	#    Remove all entries which are blank
	pared_failure_reasons = []
	for this_element in failure_reasons:
		if not this_element == "":
			pared_failure_reasons.append(this_element)
	failure_reason_text = "\n".join(pared_failure_reasons)
	make_is_correct = (failure_reason_text == "")
	try:
		cur.execute("update correctness_info set (is_correct, failure_reason) = (%s, %s) where id = %s", (make_is_correct, failure_reason_text, this_id))
	except Exception as e:
		alert("Could not update correctness_info after processing record {}: '{}'".format(this_id, e))
	cur.close()
	conn.close()
	return

###############################################################

if __name__ == "__main__":
	# Get the base for the log directory
	log_dir = "{}/Logs".format(os.path.expanduser("~"))
	if not os.path.exists(log_dir):
		os.mkdir(log_dir)
	# Set up the logging and alert mechanisms
	log_file_name = "{}/collector-log.txt".format(log_dir)
	alert_file_name = "{}/collector-alert.txt".format(log_dir)
	vp_log = logging.getLogger("logging")
	vp_log.setLevel(logging.INFO)
	log_handler = logging.FileHandler(log_file_name)
	log_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
	vp_log.addHandler(log_handler)
	vp_alert = logging.getLogger("alerts")
	vp_alert.setLevel(logging.CRITICAL)
	alert_handler = logging.FileHandler(alert_file_name)
	alert_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
	vp_alert.addHandler(alert_handler)
	def log(log_message):
		vp_log.info(log_message)
	def alert(alert_message):
		vp_alert.critical(alert_message)
		log(alert_message)
	def die(error_message):
		vp_alert.critical(error_message)
		log("Died with '{}'".format(error_message))
		exit()
	
	log("Started overall collector processing")

	# Set up directories
	
	# Where to get the incoming files
	incoming_dir = os.path.expanduser("~/Incoming")
	if not os.path.exists(incoming_dir):
		os.mkdir(incoming_dir)
	# Where to put the processed files files
	originals_dir = os.path.expanduser("~/Originals")
	if not os.path.exists(originals_dir):
		os.mkdir(originals_dir)
	# Where to save things long-term
	output_dir = os.path.expanduser("~/Output")
	if not os.path.exists(output_dir):
		os.mkdir(output_dir)

	# Connect to the database
	try:
		conn = psycopg2.connect(dbname="metrics", user="metrics")
	except Exception as e:
		die("Unable to open database: '{}'".format(e))
	try:
		cur = conn.cursor()
	except Exception as e:
		die("Unable to get database cursor: '{}'".format(e))
	try:
		conn.set_session(autocommit=True)
	except Exception as e:
		die("Unable to get set autocommit: '{}'".format(e))
	
	###############################################################

	# For each VP, find the files in /sftp/transfer/Output and get them one by one
	#   For each file, after getting, move it to /sftp/transfer/AlreadySeen

	# Get the list of VPs
	log("Started pulling from VPs")
	vp_list_filename = os.path.expanduser("~/vp_list.txt")
	try:
		all_vps = open(vp_list_filename, mode="rt").read().splitlines()
	except Exception as e:
		die("Could not open {} and split the lines: '{}'".format(vp_list_filename, e))

	total_pulled = 0
	with futures.ProcessPoolExecutor() as executor:
		for (this_vp, pulled_count) in zip(all_vps, executor.map(get_files_from_one_vp, all_vps)):
			if pulled_count:
				total_pulled += pulled_count
	log("Finished pulling from VPs; got {} files from {} VPs".format(total_pulled, len(all_vps)))

	###############################################################

	# Go through the files in ~/Incoming
	log("Started going through Incoming")
	all_files = list(glob.glob("{}/*".format(incoming_dir)))
	with futures.ProcessPoolExecutor() as executor:
		for (this_file, _) in zip(all_files, executor.map(process_one_incoming_file, all_files)):
			pass
	log("Finished processing {} files in Incoming".format(len(all_files)))

	###############################################################
	
	# Keep the set of root zones up to date
	#   If there is a new root zone, save it and also process it for matching tests later
	#   This is done after pulling the VP data to increase the chance that we'll get the latest zone before matching
	# This is not done under multiprocessing
	
	log("Started root zone collecting")

	# Subdirectories of ~/Output for root zones
	saved_root_zone_dir = "{}/RootZones".format(output_dir)
	if not os.path.exists(saved_root_zone_dir):
		os.mkdir(saved_root_zone_dir)
	saved_matching_dir = "{}/RootMatching".format(output_dir)
	if not os.path.exists(saved_matching_dir):
		os.mkdir(saved_matching_dir)
	
	# Get the current root zone
	internic_url = "https://www.internic.net/domain/root.zone"
	try:
		root_zone_request = requests.get(internic_url)
	except Exception as e:
		die("Could not do the requests.get on {}: '{}'".format(internic_url, e))
	# Save it as a temp file to use named-compilezone
	temp_latest_zone_name = "{}/temp_latest_zone".format(log_dir)
	temp_latest_zone_f = open(temp_latest_zone_name, mode="wt")
	temp_latest_zone_f.write(root_zone_request.text)
	temp_latest_zone_f.close()
	# Give the named-compilezone command, then post-process
	try:
		named_compilezone_p = subprocess.run("/home/metrics/Target/sbin/named-compilezone -q -i none -r ignore -o - . '{}'".format(temp_latest_zone_name),
			shell=True, text=True, check=True, capture_output=True)
	except Exception as e:
		die("named-compilezone failed with '{}'".format(e))
	new_root_text_in = named_compilezone_p.stdout
	# Turn tabs into spaces
	new_root_text_in = re.sub("\t", " ", new_root_text_in)
	# Turn runs of spaces into a single space
	new_root_text_in = re.sub(" +", " ", new_root_text_in)
	# Get the output after removing comments
	new_root_text = ""
	# Remove the comments
	for this_line in new_root_text_in.splitlines():
		if not this_line.startswith(";"):
			new_root_text += this_line + "\n"

	# Keep track of all the records in this temporary root zone, both to find the SOA but also to save for later matching comparisons
	root_name_and_types = {}
	for this_line in new_root_text.splitlines():
		(this_name, _, _, this_type, this_rdata) = this_line.split(" ", maxsplit=4)
		this_key = "{}/{}".format(this_name, this_type)
		if not this_key in root_name_and_types:
			root_name_and_types[this_key] = set()
		root_name_and_types[this_key].add(this_rdata)
			
	# Find the SOA record
	try:
		this_soa_record = list(root_name_and_types[("./SOA")])[0]
	except:
		die("The root zone just received didn't have an SOA record.")
	try:
		this_soa = this_soa_record.split(" ")[2]
	except Exception as e:
		die("Splitting the SOA from the root zone just received failed with '{}'".format(e))

	# Check if this SOA has already been seen
	full_root_file_name = "{}/{}.root.txt".format(saved_root_zone_dir, this_soa)
	if not os.path.exists(full_root_file_name):
		out_f = open(full_root_file_name, mode="wt")
		out_f.write(root_zone_request.text)
		out_f.close()
		log("Got a root zone with new SOA {}".format(this_soa))
		# Also create a file of the tuples for matching
		matching_file_name = "{}/{}.matching.pickle".format(saved_matching_dir, this_soa)
		out_f = open(matching_file_name, mode="wb")
		pickle.dump(root_name_and_types, out_f)
		out_f.close()

	log("Finished root zone collecting")
	
	###############################################################

	# Now that all the measurements are in, go through all records in correctness_info where is_correct is NULL
	#   This is done separately in order to catch all earlier attempts where there was not a good root zone file to compare
	#   This does not log or alert; that is left for a different program checking when is_correct is not null

	# Iterate over the records where is_correct is null
	cur.execute("select id, recent_soa, source_pickle from correctness_info where is_correct is null")
	correct_to_check = cur.fetchall()
	log("Started correctness checking on {} found".format(len(correct_to_check)))
	with futures.ProcessPoolExecutor() as executor:
		for (this_correctness_tuple, _) in zip(correct_to_check, executor.map(process_one_correctness_tuple, correct_to_check)):
			pass
	log("Finished processing {} files in Incoming".format(len(all_files)))
	
	###############################################################
	
	# STILL TO DO: Running through correctness_info where is_correct is false, using older root zones based on SOA
	#    Will likely use updating as in "update temp1 set b = b || '{"ThrEE"}' where a = 'one';"
	
	# STILL TO DO: Validation in correctness checking
	
	###############################################################
	
	cur.close()
	conn.close()
	log("Finished overall collector processing")	
	exit()

"""
	# Need the root zone file for this
	recent_soa_root_filename = "{}/{}.root.txt".format(saved_root_zone_dir, this_recent_soa_serial_array[-1])
"""