#!/usr/bin/env python3

''' Read files from ~/Incoming, add data to the database, move them to ~/Originals/yyyymm/ '''
# Run as the metrics user
# Run from cron job every 30 minutes

# Three-letter items in square brackets (such as [xyz]) refer to parts of rssac-047.md

import datetime, logging, os, psycopg2, subprocess

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

	log("Finished measurements")

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

