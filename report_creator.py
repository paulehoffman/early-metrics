#!/usr/bin/env python3

''' Create the monthly reports '''
# Run as the metrics user
# Three-letter items in square brackets (such as [xyz]) refer to parts of rssac-047.md

import argparse, datetime, glob, gzip, logging, os, pickle, psycopg2, socket, subprocess, shutil, tempfile, yaml

if __name__ == "__main__":
	# Get the base for the log directory
	log_dir = "{}/Logs".format(os.path.expanduser("~"))
	if not os.path.exists(log_dir):
		os.mkdir(log_dir)
	# Set up the logging and alert mechanisms
	log_file_name = "{}/report-log.txt".format(log_dir)
	alert_file_name = "{}/report-alert.txt".format(log_dir)
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
	
	# Where the binaries are
	target_dir = "/home/metrics/Target"
	
	this_parser = argparse.ArgumentParser()
	this_parser.add_argument("--weekly", action="store_true", dest="weekly",
		help="Create weekly reports; this will be implemented later")
	opts = this_parser.parse_args()

	# Subdirectories of ~/Output for the reports
	output_dir = os.path.expanduser("~/Output")
	if not os.path.exists(output_dir):
		os.mkdir(output_dir)
	monthly_reports_dir = "{}/Monthly".format(output_dir)
	if not os.path.exists(monthly_reports_dir):
		os.mkdir(monthly_reports_dir)

	log("Started report process")
	
	##############################################################
	
	# See if a monthly report needs to be written
	now = datetime.datetime.utcnow()
	now_datestring = now.strftime("%Y-%m-%d")
	this_month_number = now.month
	# Math is different if it is currently January
	if not now.month == 1:
		first_of_last_month = now.replace(month=(now.month - 1), day=1)
	else:
		first_of_last_month = now.replace(year=(now.year - 1), month=12, day=1)
	first_of_last_month_datestring = first_of_last_month.strftime("%Y-%m-%d")
	log("It is now {}, the first of last month is {}".format(now_datestring, first_of_last_month_datestring))
	# Look for a report for last month
	all_monthly_reports = glob.glob("{}/monthly*.txt".format(monthly_reports_dir))
	for this_report in glob.glob("{}/monthly-*.txt".format(monthly_reports_dir)):
		if first_of_last_month_datestring in this_report:
			die("Found {}, so no need to create it.".format(this_report))
	# Here if a monthly report needs to be made
	new_monthly_report_name = "{}/monthly-{}.txt".format(monthly_reports_dir, first_of_last_month_datestring)
	log("About to create {}".format(new_monthly_report_name))

	exit() #################################

	##############################################################

	# Connect to the database
	try:
		conn = psycopg2.connect(dbname="metrics", user="metrics")
	except Exception as e:
		die("Unable to open database: '{}'".format(e))
	try:
		cur = conn.cursor()
	except Exception as e:
		die("Unable to get database cursor: '{}'".format(e))
	
	
	cur.close()
	conn.close()
	log("Finished report process")	
	exit()
