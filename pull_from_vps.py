#!/usr/bin/env python3

''' Use sftp to pull from all VPs to ~/Incoming '''
# Run as the metrics user
# Run from cron job every 30 minutes

# Three-letter items in square brackets (such as [xyz]) refer to parts of rssac-047.md

import logging, os, paramiko, psycopg2

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
	
	# Connect to the database
	try:
		conn = psycopg2.connect(dbname="metrics", user="metrics")
	except Exception as e:
		die("Unable to open database: '{}'".format(e))
	try:
		cur = conn.cursor()
	except Exception as e:
		die("Unable to get database cursor: '{}'".format(e))
	
	# Where to save the incoming files
	input_dir = os.path.expanduser("~/Incoming")
	if not os.path.exists(input_dir):
		os.mkdir(input_dir)

	# Update the vp_names table to have everything in ~/vp_list.txt
	vp_list_filename = os.path.expanduser("~/vp_list.txt")
	try:
		all_vps_from_file = open(vp_list_filename, mode="rt").read().splitlines()
	except Exception as e:
		die("Could not open {} and split the lines: '{}'".format(vp_list_filename, e))
	all_vps_from_db = []
	try:
		cur.execute("select name from vp_names;")
		all_vp_tuples_from_db = cur.fetchall()
	except Exception as e:
		die("Could not fetch all the names from vp_names: '{}'".format(e))
	all_vps_from_db = []
	for this_tuple in all_vp_tuples_from_db:
		all_vps_from_db.append(this_tuple[0])
	print("{}\n{}".format(all_vps_from_file, all_vps_from_db))
	
	exit() ##################################
	
	# Find the last file received from each VP
	for this_vp in all_vps:
		pass ####################
		