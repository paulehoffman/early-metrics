#!/usr/bin/env python3

''' Get root zone for collector and save all new copies '''
# Run as the metrics user
# Stores zones in ~/Output/RootZones
# Run from cron job every 30 minutes
# Process zone file with named-compilezone, look for SOA
#   If not already there, name new file _soa_.root.txt

# Three-letter items in square brackets (such as [xyz]) refer to parts of rssac-047.md

import logging, os, pickle, re, requests, subprocess

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
	def die(error_message):
		vp_alert.critical(error_message)
		log("Died with '{}'".format(error_message))
		exit()
	
	# Where to save things long-term
	output_dir = os.path.expanduser("~/Output")
	if not os.path.exists(output_dir):
		os.mkdir(output_dir)
	saved_root_zone_dir = "{}/RootZones".format(output_dir)
	if not os.path.exists(saved_root_zone_dir):
		os.mkdir(saved_root_zone_dir)
	saved_matching_dir = "{}/RootMatching".format(output_dir)
	if not os.path.exists(saved_matching_dir):
		os.mkdir(saved_matching_dir)
	# Get the current root zone
	internic_url = "https://www.internic.net/domain/root.zone"
	try:
		r = requests.get(internic_url)
	except Exception as e:
		die("Could not do the requests.get on {}: '{}'".format(internic_url, e))
	# Save it as a temp file to use named-compilezone
	temp_latest_zone_name = "{}/temp_latest_zone".format(log_dir)
	temp_latest_zone_f = open(temp_latest_zone_name, mode="wt")
	temp_latest_zone_f.write(r.text)
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
	# Keep track of all the records, both to find the SOA but also to save for later matching comparisons
	root_name_and_types = {}
	for his_line in new_root_text.splitlines():
		(this_name, _, _, this_type, rdata) = this_line.split(" ", maxsplit=4)
		this_key = "{}/{}".format(this_name, this_type)
		if this_key in root_name_and_types:
			root_name_and_types[this_key].append(rdata)
		else:
			root_name_and_types[this_key] = [ rdata ]
	# Find the SOA record
	try:
		this_soa_record = root_name_and_types[("./SOA")][0]
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
		out_f.write(new_root_text)
		out_f.close()
		log("Got a root zone with new SOA {}".format(this_soa))
		# Also create a file of the tuples for matching
		matching_file_name = "{}/{}.matching.pickle".format(saved_matching_dir, this_soa)
		out_f = open(matching_file_name, mode="wb")
		pickle.dump(root_name_and_types, out_f)
		out_f.close()
	exit()
	