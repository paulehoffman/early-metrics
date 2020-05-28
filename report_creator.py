#!/usr/bin/env python3

''' Create the monthly reports '''
# Run as the metrics user
# Three-letter items in square brackets (such as [xyz]) refer to parts of rssac-047.md

import argparse, datetime, glob, logging, os, psycopg2

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
	this_parser.add_argument("--test_date", action="store", dest="test_date",
		help="Give a date as YY-MM-DD-HH-MM-SS to act as today")
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
	strf_day_format = "%Y-%m-%d"
	strf_timestamp_format = "%Y-%m-%d %H:%M:%S"
	if opts.test_date:
		parts = opts.test_date.split("-")
		if not len(parts) == 6:
			die("Must give test_date as YY-MM-DD-HH-MM-SS")
		try:
			now = datetime.datetime(int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5]))
		except Exception as e:
			die("Could not parse {} into YY-MM-DD-HH-MM-SS: {}".format(opts.test_date, e))
		log("Using test date of {}, which becomes '{}'".format(opts.test_date, now))
	else:
		now = datetime.datetime.utcnow()
	this_month_number = now.month
	# Math is different if it is currently January
	if not now.month == 1:
		first_of_last_month = now.replace(month=(now.month - 1), day=1, hour=0, minute=0, second=0)
	else:
		first_of_last_month = now.replace(year=(now.year - 1), month=12, day=1)
	first_of_last_month_file = first_of_last_month.strftime(strf_day_format)
	first_of_last_month_timestamp = first_of_last_month.strftime(strf_timestamp_format)
	end_of_last_month =  now.replace(day=1, hour=0, minute=0, second=0) - datetime.timedelta(seconds=1)
	end_of_last_month_timestamp = end_of_last_month.strftime(strf_timestamp_format)
	log("It is now {}, the first of last month is {}".format(now.strftime("%Y-%m-%d"), first_of_last_month_file))
	# Look for a report for last month
	all_monthly_reports = glob.glob("{}/monthly*.txt".format(monthly_reports_dir))
	for this_report in glob.glob("{}/monthly-*.txt".format(monthly_reports_dir)):
		if first_of_last_month_file in this_report:
			die("Found {}, so no need to create it.".format(this_report))
	# Here if a monthly report needs to be made
	new_monthly_report_name = "{}/monthly-{}.txt".format(monthly_reports_dir, first_of_last_month_file)
	log("About to create {} for range {} to {}".format(new_monthly_report_name, first_of_last_month_timestamp, end_of_last_month_timestamp))

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
	
	# Get all the SOA records for this month
	cur.execute("select rsi, internet, transport, dig_elapsed, timeout, soa from public.soa_info "\
		+ "where date_derived between '{}' and  '{}'".format(first_of_last_month_timestamp, end_of_last_month_timestamp))
	soa_recs = cur.fetchall()
	log("Found {} SOA records".format(len(soa_recs)))
	
	##############################################################
	
	# RSIs to report on
	#    The list of RSIs might change in the future, so treat this as a list [dlw]
	rsi_list = [ "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m" ]
	
	# Go through the SOA records, storing results for availability and response latency
	rsi_availability = {}
	rsi_response_latency = {}
	for this_rsi in rsi_list:
		# For availability, each internet_transport_pair has two values: number of timeouts, and count
		rsi_availability[this_rsi] = { "v4udp": [ 0, 0 ], "v4tcp": [ 0, 0 ], "v6udp": [ 0, 0 ], "v6tcp": [ 0, 0 ] }
		# For response latency, each internet_transport_pair has two values: sum of response latencies, and count
		rsi_response_latency[this_rsi] = { "v4udp": [ 0, 0 ], "v4tcp": [ 0, 0 ], "v6udp": [ 0, 0 ], "v6tcp": [ 0, 0 ] }
	for this_rec in soa_recs:
		(this_rsi, this_internet, this_transport, this_dig_elapsed, this_timeout, this_soa) = this_rec
		internet_transport_pair = this_internet + this_transport
		# Availability [gfa]
		if this_timeout:
			rsi_availability[this_rsi][internet_transport_pair][0] += 1
		rsi_availability[this_rsi][internet_transport_pair][1] += 1
		# Response latency
		rsi_response_latency[this_rsi][internet_transport_pair][0] += this_dig_elapsed
		rsi_response_latency[this_rsi][internet_transport_pair][1] += 1
	
		
	
	cur.close()
	conn.close()
	log("Finished report process")	
	exit()
