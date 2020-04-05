#!/usr/bin/env python3

''' Read files from ~/Incoming, add data to the database, move them to ~/Originals/yyyymm/ '''
# Run as the metrics user
# Run from cron job every 30 minutes
# Note that this does not perform the correctness calculations

# Three-letter items in square brackets (such as [xyz]) refer to parts of rssac-047.md

import datetime, gzip, logging, os, psycopg2, subprocess

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
	
	log("Started measurements")
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
	
	# Where to get the incoming files
	incoming_dir = os.path.expanduser("~/Incoming")
	if not os.path.exists(incoming_dir):
		os.mkdir(incoming_dir)
	# Where to put the processed files files
	originals_dir = os.path.expanduser("~/Originals")
	if not os.path.exists(originals_dir):
		os.mkdir(originals_dir)

	# Go throug the files in ~/Incoming
	for this_file in glob.glob("{}/*".format(incoming_dir_):
		if not this_file.endswith(".gz"):
			vp_alert.critical("Found {} that did not end in .gz".format(this_file))
			continue
		# Ungz it
		try:
			with gzip.open(this_file, mode="rb") as pf:
				in_pickle = pf.read()
		except Exception as e:
			die("Could not unzip {}: '{}'".format(this_file, e))
		# Unpickle it
		try:
			in_obj = pickle.loads(in_pickle)
		except Exception as e:
			die("Could not unpickle {}: '{}'".format(this_file, e))
		# Log the metadata
		if not ("d" in in_obj) and ("e" in in_obj) and ("r" in in_obj) and ("s" in in_obj) and ("v" in in_obj):
			die("Object in {} did not contain keys d, e, r, s, and v".format(this_file))
		update_string = "update files_gotten set processed_at=%s, version=%s, delay=%s, elapsed=%s where filename_full=%s"
		update_vales = (datetime.datetime.now(datetime.timezone.utc), in_obj["v"], in_obj["d"], in_obj["e"], this_file) 
		try:
			cur.execute(update_string, update_vales)
		except Exception as e:
			die("Could not insert '{}' into files_gotten: '{}'".format(this_filename, e))

	log("Finished measurements")
	exit()

"""
files_gotten
 filename_full | text                       
 retrieved_at  | timestamp without time zone
 + processed_at | timestamp without time zone
 + version | int
 + delay | int
 + elapsed | int

route_info
 file_prefix | text
 date_derived | timestamp without time zone
 vp | text
 route_string | text

soa_info
 file_prefix | text
 date_derived | timestamp without time zone
 vp | text
 rsi | text
 internet | text
 transport | text
 prog_elapsed | real
 dig_elapsed | real
 timeout | boolean
 soa | text

correctness_info
 file_prefix | text
 date_derived | timestamp without time zone
 vp | text
 rsi | text
 internet | text
 transport | text
 is_correct | boolean
 source_pickle | bytes

"""

