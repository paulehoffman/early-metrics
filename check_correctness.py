#!/usr/bin/env python3

''' Find records in the correctness table that have not been checked, and check them '''
# Run as the metrics user
# Run from cron job every 30 minutes
# Reports why any failure happens

# Three-letter items in square brackets (such as [xyz]) refer to parts of rssac-047.md

import datetime, logging, psycopg2, subprocess

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
	log_handler.setFormatter(logging.Formatter("%(created)d %(message)s"))
	vp_log.addHandler(log_handler)
	vp_alert = logging.getLogger("alerts")
	vp_alert.setLevel(logging.CRITICAL)
	alert_handler = logging.FileHandler(alert_file_name)
	alert_handler.setFormatter(logging.Formatter("%(created)d %(message)s"))
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
	
	log("Started correctness checking")
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
		die("Unable to turn on autocommit: '{}'".format(e))
	
	checked_count = 0
	try:
		cur.execute("select (id, source_pickle) from correctness_info where is_correct is null")
	except Exception as e:
		die("Unable to do select: '{}'".format(e))
	for this_record in cur:
		(this_id, this_source) = this_record
		####### Determine correctness (boolean) and failure_text
		try:
			this_dig = pickle.loads(this_source)
		except Exception as e:
			die("Could not unpickle id {}: '{}'".format(this_id, e))
		try:
			this_message = this_dig["message"]
		except Exception as e:
			die("Found no message in id {}: '{}'".format(this_id, e))
		try:
			this_data = this_message["response_message_data"]
		except Exception as e:
			die("Found no response_message_data in id {}: '{}'".format(this_id, e))
		needs_updating = False
		if needs_updating:
			try:
				cur.execute("update correctness_info set (is_correct, failure_reason) = (%s, %s) where id = this_id", (correctness, failure_text))
			except Exception as e:
				die("Unable to get update correctness_info: '{}'".format(e))
		checked_count += 1
	
	log("Finished correctness checking, processed {} records".format(checked_count))
	exit()

"""
							this_matching_log = check_for_matching(dig_dict["message"]["response_time"].timestamp(), this_data)
							# Log the errors
							if this_matching_log:
								log(this_matching_log)
								this_correctness = False
							else:
								this_correctness = True
"""

"""
def check_for_matching(timestamp_of_response, in_data):
	''' Checks response for matching against 48 hours of zone file, and returns a log message if the match failed, otherwise returns "Matched"
	    Note that if any day matches, this returns "Matched" immediately '''
	# Check for a bad status
	if not (in_data["status"] in ("NOERROR", "NXDOMAIN")):
		return "Unexpected status of {} in data {}".format(in_data["status"], in_data)
	# Make a list of all root zones from the 48 hours before the request
	these_processed_roots = []
	for this_file in sorted(glob.glob("{}/*".format(root_zones_processed_dir))):
		this_mdate = os.stat(this_file)[8]
		if (this_mdate >= int(timestamp_of_response) - 172800) and (this_mdate <= int(timestamp_of_response)):
			these_processed_roots.append(this_file)
	if len(these_processed_roots) == 0:
		return "Found no root zones in the past 48 hours for {} in {}".format(timestamp_of_response, in_data)
	all_day_returns = {}
	for this_zone_file in sorted(these_processed_roots, reverse=True):
		this_day_return = check_one_day_for_matching(in_data, this_zone_file)
		# If this day returns "Matched" (full match), return to the calling program
		if this_day_return == "Matched":
			return "Matched"
		else:
			all_day_returns[os.path.splitext(os.path.basename(this_zone_file))[0]] = this_day_return
	# Here if none of the zone files returned with a match
	failure_return_text = "Matching failed:\n"
	for this_day in sorted(all_day_returns):
		failure_return_text += "{}: {}\n".format(this_day, all_day_returns[this_day])
	return failure_return_text

def check_one_day_for_matching(in_data, this_zone_file):
	(this_soa, _) = os.path.splitext(os.path.basename(this_zone_file))
	try:
		f_in = open(this_zone_file, mode="rt")
		processed_root_dict = json.load(f_in)
	except:
		return "Could not read JSON from {}.".format(this_zone_file)
	# All of the RRsets in the Answer, Authority, and Additional sections match RRsets found in the zone.
	#   Note that "dig" does not put the OPT RRset in the ADDITIONAL_SECTION, so no special checking for that is needed here.
	all_section_rdatas = {}
	for this_section in ("ANSWER_SECTION", "AUTHORITY_SECTION", "ADDITIONAL_SECTION"):
		for this_response_record in in_data.get(this_section, []):
			(rec_qname, _, _, rec_qtype, rec_rdata) = this_response_record.split(" ", maxsplit=4)
			slash_pair = "{}/{}".format(rec_qname, rec_qtype)
			# Check whether the qname/qtype exists in the root zone
			if not slash_pair in processed_root_dict:
				return "Matching: did not find {} from {}: {}".format(slash_pair, this_section, in_data)
			if not all_section_rdatas.get(slash_pair):
				all_section_rdatas[slash_pair] = set([rec_rdata])
			else:
				all_section_rdatas[slash_pair].add(rec_rdata)
		# Check that the Rdata sets are identical in the response and in the zone
		for this_slash_pair in all_section_rdatas:
			# Don't report mis-matched ./SOA because this is expected for a set
			if (this_slash_pair == "./SOA") and (not os.path.splitext(this_soa) in all_section_rdatas[this_slash_pair]):
				continue
			# Don't check for RRSIG RRsets here they will be checked individually by target type
			if rec_qtype == "RRSIG":
				continue
			zone_rdatas = set(processed_root_dict[this_slash_pair])
			if len(all_section_rdatas[this_slash_pair] ^ zone_rdatas) > 0:
					# Because these can be long, add \n between each record
					out_section = "\n".join(all_section_rdatas[this_slash_pair])
					out_zone = "\n".join(zone_rdatas)
					return "Not matched identical: Rdataset for {}\n{}\ndid not match one in zone\n{}".format(this_slash_pair, out_section, out_zone)
	# Get the qname and qtype
	this_question = in_data["QUESTION_SECTION"][0]
	try:
		(this_qname, _, this_qtype) = this_question.split(" ")
	except:
		return "Could not split the question section in {}".format(in_data)
	# The tests are different for positive and negative return values
	if in_data["status"] == "NOERROR":
		# Processing for TLD / NS
		if (this_qname != ".") and (this_qtype == "NS"):
			# The header AA bit is not set
			if "aa" in in_data["flags"]:
				return "Not matched TLD/NS: AA was set: {}".format(in_data)
			# The Answer section is empty
			if in_data.get("ANSWER_SECTION"):
				return "Not matched TLD/NS: Answer section was not empty: {}".format(in_data)
			# The Authority section contains the entire NS RRset for the query name
			dig_authority_set = get_RRset_from_section(in_data["AUTHORITY_SECTION"], this_qname, "NS")
			root_set = set(processed_root_dict.get("{}/NS".format(this_qname)))
			if len(dig_authority_set ^ root_set) > 0:
				return "Not matched TLD/NS: NS in Authority {} did not match one in zone {}".format(dig_authority_set, root_set)
			# Check if the DS RRset for the query name exists in the zone
			if processed_root_dict.get("{}/DS".format(this_qname)):
				# The Authority section contains the signed DS RRset for the query name
				if not FAKE_check_signed_rrset(in_data["AUTHORITY_SECTION"], this_qname, "DS"):
					return "Not matched TLD/NS with DS: {}/DS in Authority section did not exist or was not validated".format(this_qname)
			else:
				# The Authority section contains no DS RRset
				ds_in_dig_authority = get_RRset_from_section(in_data["AUTHORITY_SECTION"], "*", "DS")
				if len(ds_in_dig_authority) > 0:
					return "Not matched TLD/NS without DS: there was a different DS in the Authority section {}".format(ds_in_dig_authority)
				# The Authority section contains a signed NSEC RRset covering the query name.
				if not FAKE_get_covering_nsec(in_data["AUTHORITY_SECTION"], this_qname, "NS"):
					return "Not matched TLD/NS without DS: the covering NSEC for {}/{} was not found or was not validated".format(this_qname, "NS")
			return "Matched"
		elif (this_qname != ".") and (this_qtype == "DS"):
			# The header AA bit is set
			if not "aa" in in_data["flags"]:
				return "Not matched TLD/DS: AA was not set: {}".format(in_data)
			# The Answer section contains the signed DS RRset for the query name.
			if not FAKE_check_signed_rrset(in_data["ANSWER_SECTION"], this_qname, "DS"):
				return "Not matched TLD/DS: {}/DS in Answer section did not exist or was not validated".format(this_qname)
			# The Authority section is empty
			if in_data.get("AUTHORITY_SECTION"):
				return "Not matched TLD/DS {} {}: Authority section was not empty: {}".format(this_qname, this_qtype, in_data["AUTHORITY_SECTION"])
			# The Additional section is empty
			if in_data.get("ADDITIONAL_SECTION"):
				return "Not matched TLD/DS {} {}: Additional section was not empty: {}".format(this_qname, this_qtype, in_data["ADDITIONAL_SECTION"])
			return "Matched"
		elif (this_qname == ".") and (this_qtype == "SOA"):
			# The header AA bit is set
			if not "aa" in in_data["flags"]:
				return "Not matched ./SOA: AA was not set: {}".format(in_data)
			# The Answer section contains the signed SOA record for the root.
			answer_section_records = in_data["ANSWER_SECTION"]
			matched_soa_record = ""
			for this_record in answer_section_records:
				(answer_qname, _, _, answer_qtype, answer_rdata) = this_record.split(" ", maxsplit=4)
				if answer_qname == "." and answer_qtype == "SOA":
					(_, _, internal_soa, _) = answer_rdata.split(" ", maxsplit=3)
					if not internal_soa == this_soa:
						return "Not matched ./SOA: the SOA record found in the Answer, {}, did not match the zone SOA {}".format(internal_soa, this_soa)
					else:
						matched_soa_record = this_record
						break
			if matched_soa_record == "":
				return "Not matched ./SOA: no matching SOA record found in the Answer"
			if not FAKE_check_signed_rrset(in_data["ANSWER_SECTION"], ".", "SOA"):
				return "Not matched ./SOA: ./SOA in Answer section was not validated"
			# The Authority section contains the signed NS RRset for the root.
			if not FAKE_check_signed_rrset(in_data["AUTHORITY_SECTION"], ".", "NS"):
				return "Not matched ./SOA: ./NS in Authority section did not exist or was not validated"
			return "Matched"
		elif (this_qname == ".") and (this_qtype == "NS"):
			# The header AA bit is set
			if not "aa" in in_data["flags"]:
				return "Not matched ./NS: AA was not set: {}".format(in_data)
			# The Answer section contains the signed NS RRset for the root.
			if not FAKE_check_signed_rrset(in_data["ANSWER_SECTION"], ".", "NS"):
				return "Not matched ./NS: ./NS in Answer section did not exist or was not validated"
			# The Authority section is empty.
			if in_data.get("AUTHORITY_SECTION"):
				return "Not matched ./NS: Authority section was not empty: {}".format(in_data["AUTHORITY_SECTION"])
			return "Matched"
		elif (this_qname == ".") and (this_qtype == "DNSKEY"):
			# The header AA bit is set
			if not "aa" in in_data["flags"]:
				return "Not matched ./DNSKEY: AA was not set: {}".format(in_data)
			# The Answer section contains the signed DNSKEY RRset for the root.
			if not FAKE_check_signed_rrset(in_data["ANSWER_SECTION"], ".", "DNSKEY"):
				return "Not matched ./DNSKEY: DNSKEY in Answer section did not exist or was not validated"
			# The Authority section is empty.
			if in_data.get("AUTHORITY_SECTION"):
				return "Not matched ./DNSKEY: Authority section was not empty: {}".format(in_data["AUTHORITY_SECTION"])
			# The Additional section is empty.
			if in_data.get("ADDITIONAL_SECTION"):
				return "Not matched ./DNSKEY: Additional section was not empty: {}".format(in_data["AUTHORITY_SECTION"])
			return "Matched"
		else:
			return "Not matched: when checking NOERROR statuses, found unexpected name/type of {}/{}".format(this_qname, this_qtype)
	elif in_data["status"] == "NXDOMAIN":
		# The header AA bit is set
		if not "aa" in in_data["flags"]:
			return "Not matched NXDOMAIN: AA was not set: {}".format(in_data)
		# The Answer section is empty
		if not in_data["ANSWER"] == 0:
			return "Not matched NXDOMAIN: Answer section was not empty: {}".format(in_data)
		### The Authority section contains the signed . / SOA record.
		if not FAKE_check_signed_rrset(in_data["AUTHORITY_SECTION"], ".", "SOA"):
			return "Not matched NXDOMAIN: ./SOA in Authority section did not exist or was not validated"
		### The Authority section contains a signed NSEC record covering the query name.
		if not FAKE_get_covering_nsec(in_data["AUTHORITY_SECTION"], this_qname, this_qtype):
			return "Not matched NXDOMAIN: the covering NSEC for {}/{} was not found or was not validated".format(this_qname, this_qtype)
		### The Authority section contains a signed NSEC record with owner name “.” proving no wildcard.
		############ pass
		# The Additional section is empty
		if in_data.get("ADDITIONAL_SECTION"):
			return "Not matched NXDOMAIN {}/{}: Additional section was not empty: {}".format(this_qname, this_qtype, in_data["ADDITIONAL_SECTION"])
		# Here if there was no failure in the NXDOMAIN cases
		return "Matched"
	else:
		return "Got to end of check_for_matching in an unexpected fashion for {}".format(in_data)

def get_RRset_from_section(section_as_list, in_qname, in_qtype):
	''' Returns a set that is the RRset with the given qname and qtype '''
	set_to_return = set()
	for this_element in section_as_list:
		(this_qname, _, _, this_qytpe, this_rdata) = this_element.split(" ", maxsplit=4)
		if ((this_qname == in_qname) or (this_qname == "*")) and this_qytpe == in_qtype:
			set_to_return.add(this_rdata)
	return set_to_return

def FAKE_check_signed_rrset(section_as_list, in_qname, in_qtype):
	''' Returns true if the RRset exists in the section and the signature on that RRset validates '''
	# VERY IMPORTANT NOTE
	#   This code does nothing. Eventual code really should do something.	
	#   Having said that, if someone wants to fix this code, that would be grand.
	return True

def FAKE_get_covering_nsec(section_as_list, in_qname, in_qtype):
	''' Returns true if the section has an NSEC record that covers the qname/qtype, and the signature on that NSEC validates '''
	# VERY IMPORTANT NOTE
	#   This code does nothing. Eventual code really should do something.	
	#   Having said that, if someone wants to fix this code, that would be grand.
	return True
				
"""
