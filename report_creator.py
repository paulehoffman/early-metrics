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
	end_of_last_month =  now.replace(day=1, hour=0, minute=0, second=0) - datetime.timedelta(seconds=1)  # [ver] [jps]
	end_of_last_month_timestamp = end_of_last_month.strftime(strf_timestamp_format)
	log("It is now {}, the first of last month is {}".format(now.strftime("%Y-%m-%d"), first_of_last_month_file))
	# Look for a report for last month
	all_monthly_reports = glob.glob("{}/monthly*.txt".format(monthly_reports_dir))
	for this_report in glob.glob("{}/monthly-*.txt".format(monthly_reports_dir)):
		if first_of_last_month_file in this_report:
			die("Found {}, so no need to create it.".format(this_report))  # [rps]
	# Here if a monthly report needs to be made
	new_monthly_report_name = "{}/monthly-{}.txt".format(monthly_reports_dir, first_of_last_month_file)
	log("About to create {} for range {} to {}".format(new_monthly_report_name, first_of_last_month_timestamp, end_of_last_month_timestamp))
	# Start the report text
	report_text = "Report for {} to {}\n".format(first_of_last_month_timestamp, end_of_last_month_timestamp)

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
	
	# Keep track of the files seen in order to count the number of measurements across all vantage points
	#   This will be filled in both in looking through the SOA and correctness datasets
	files_seen = set()
	# The list of RSIs might change in the future, so treat this as a list [dlw]
	rsi_list = [ "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m" ]

	##############################################################

	# Get all the SOA records for this month
	cur.execute("select file_prefix, date_derived, rsi, internet, transport, dig_elapsed, timeout, soa from public.soa_info "\
		+ "where date_derived between '{}' and  '{}' order by date_derived".format(first_of_last_month_timestamp, end_of_last_month_timestamp))
	soa_recs = cur.fetchall()
	log("Found {} SOA records".format(len(soa_recs)))
	
	# Get the results for availability and response latency and response latency
	rsi_availability = {}
	rsi_response_latency = {}
	rsi_publication_latency_lowest_soa = {}
	for this_rsi in rsi_list:
		# For availability, each internet_transport_pair has two values: number of non-timeouts, and count
		rsi_availability[this_rsi] = { "v4udp": [ 0, 0 ], "v4tcp": [ 0, 0 ], "v6udp": [ 0, 0 ], "v6tcp": [ 0, 0 ] }
		# For response latency, each internet_transport_pair has two values: sum of response latencies, and count
		rsi_response_latency[this_rsi] = { "v4udp": [ 0, 0 ], "v4tcp": [ 0, 0 ], "v6udp": [ 0, 0 ], "v6tcp": [ 0, 0 ] }
		# For publication latency, record the SOA for each internet_transport_pair for a particular datetime
		rsi_publication_latency_lowest_soa[this_rsi] = { }
	# Measurements for publication latency requires more work because the system has to determine when new SOAs are first seen
	#   soa_first_seen keys are SOAs, values are the date first seen
	soa_first_seen = {}
	for this_rec in soa_recs:
		(this_file_prefix, this_date, this_rsi, this_internet, this_transport, this_dig_elapsed, this_timeout, this_soa) = this_rec
		files_seen.add(this_file_prefix)
		internet_transport_pair = this_internet + this_transport
		# Availability [gfa]
		if not this_timeout:
			rsi_availability[this_rsi][internet_transport_pair][0] += 1
		rsi_availability[this_rsi][internet_transport_pair][1] += 1
		# Response latency [fhw]
		if this_dig_elapsed:
			rsi_response_latency[this_rsi][internet_transport_pair][0] += this_dig_elapsed
			rsi_response_latency[this_rsi][internet_transport_pair][1] += 1
		# Publication latency  # [yxn]
		#   Stort the date that a SOA was first seen; note that this relies on soa_recs to be ordered by date_derived
		if not this_soa in soa_first_seen:
			if this_soa:
				soa_first_seen[this_soa] = this_date
		#    Store the minimum SOA that was seen [cnj]
		#    Timed-out responses don't count for publication latency  # [tub]
		if not this_timeout:
			if not rsi_publication_latency_lowest_soa[this_rsi].get(this_date):
				rsi_publication_latency_lowest_soa[this_rsi][this_date] = this_soa
			elif this_soa < rsi_publication_latency_lowest_soa[this_rsi][this_date]: 
				rsi_publication_latency_lowest_soa[this_rsi][this_date] = this_soa
	
	##############################################################

	# Get all the correctness records for this month
	cur.execute("select file_prefix, date_derived, rsi, is_correct from public.correctness_info "\
		+ "where date_derived between '{}' and  '{}' order by date_derived".format(first_of_last_month_timestamp, end_of_last_month_timestamp))
	correctness_recs = cur.fetchall()
	log("Found {} correctness records".format(len(correctness_recs)))
	
	# Get the results for availability and response latency and response latency
	rsi_correctness = {}
	for this_rsi in rsi_list:
		# For correcness, there are two values: number of incorrect responses, and count [jof] [lbl]
		rsi_correctness[this_rsi] = [ 0, 0 ]
	for this_rec in correctness_recs:
		(this_file_prefix, this_date, this_rsi, this_correctness) = this_rec
		files_seen.add(this_file_prefix)
		if not this_correctness:
			rsi_correctness[this_rsi][0] += 1
		rsi_correctness[this_rsi][1] += 1
		
	##############################################################

	# Note the number of measurements for this month
	report_text += "Number of measurments across all vantage points in the month: {}\n".format(len(files_seen))
	
	report_pairs = { "v4udp": "IPv4 UDP", "v4tcp": "IPv4 TCP", "v6udp": "IPv6 UDP", "v6tcp": "IPv6 TCP", }
	
	# Create the availability report
	rsi_availability_threshold = .96  # [ydw]
	report_text += "\nRSI Availability\nThreshold: {:.0f}%\n".format(rsi_availability_threshold * 100)  # [vmx]
	for this_rsi in rsi_list:
		report_text += "{}.root-servers.net:\n".format(this_rsi)
			# rsi_availability[this_rsi] = { "v4udp": [ 0, 0 ], "v4tcp": [ 0, 0 ], "v6udp": [ 0, 0 ], "v6tcp": [ 0, 0 ] }
		for this_pair in sorted(report_pairs):
			this_ratio = rsi_availability[this_rsi][this_pair][0] / rsi_availability[this_rsi][this_pair][1]
			if  this_ratio < rsi_availability_threshold:
				this_result = "Fail"
			else:
				this_result = "Pass"
			# ratio_text = "{:.0f}".format(this_ratio)  # Only used in debugging
			# report_text += "  {}: {} ({} measurements)  {}\n".format(report_pairs[this_pair], this_result, rsi_availability[this_rsi][this_pair][1], ratio_text)
			report_text += "  {}: {} ({} measurements)\n".format(report_pairs[this_pair], this_result, rsi_availability[this_rsi][this_pair][1])
		report_text += "\n"
	
	# Remove this print statement before finishing
	print("{}".format(report_text))  ################################

	cur.close()
	conn.close()
	log("Finished report process")	
	exit()
