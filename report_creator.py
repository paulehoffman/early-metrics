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
		first_of_last_month = now.replace(year=(now.year - 1), month=12, day=1, hour=0, minute=0, second=0)
	first_of_last_month_file = first_of_last_month.strftime(strf_day_format)
	first_of_last_month_timestamp = first_of_last_month.strftime(strf_timestamp_format)
	end_of_last_month =  now.replace(day=1, hour=0, minute=0, second=0) - datetime.timedelta(seconds=1)  # [ver] [jps]
	end_of_last_month_timestamp = end_of_last_month.strftime(strf_timestamp_format)
	log("It is now {}, the first of last month is {}".format(now.strftime("%Y-%m-%d"), first_of_last_month_file))
	# Look for a report for last month
	all_monthly_reports = glob.glob("{}/monthly*.txt".format(monthly_reports_dir))
	for this_report in glob.glob("{}/monthly-*.txt".format(monthly_reports_dir)):
		if first_of_last_month_file in this_report:
			log("Found {}, so no need to create it.".format(this_report))  # [rps]
			exit()
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
	
	##############################################################

	# Keep track of the files seen in order to count the number of measurements across all vantage points
	#   This will be filled in both in looking through the SOA and correctness datasets
	files_seen = set()
	# The list of RSIs might change in the future, so treat this as a list [dlw]
	rsi_list = [ "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m" ]

	# The following is used for keeping track of the internet/transport pairs, and the way they are expressed in the report
	report_pairs = { "v4udp": "IPv4 UDP", "v4tcp": "IPv4 TCP", "v6udp": "IPv6 UDP", "v6tcp": "IPv6 TCP" }

	##############################################################

	# Get all the SOA records for this month
	cur.execute("select file_prefix, date_derived, rsi, internet, transport, dig_elapsed, timeout, soa from public.soa_info "\
		+ "where date_derived between '{}' and  '{}' order by date_derived".format(first_of_last_month_timestamp, end_of_last_month_timestamp))
	soa_recs = cur.fetchall()
	log("Found {} SOA records".format(len(soa_recs)))
	
	# Get the results for availability and response latency and response latency
	rsi_availability = {}
	rsi_response_latency = {}
	rsi_publication_latency = {}
	for this_rsi in rsi_list:
		# For availability, each internet_transport_pair has two values: number of non-timeouts, and count
		rsi_availability[this_rsi] = { "v4udp": [ 0, 0 ], "v4tcp": [ 0, 0 ], "v6udp": [ 0, 0 ], "v6tcp": [ 0, 0 ] }
		# For response latency, each internet_transport_pair has two values: list of response latencies, and count
		rsi_response_latency[this_rsi] = { "v4udp": [ [], 0 ], "v4tcp": [ [], 0 ], "v6udp": [ [], 0 ], "v6tcp": [ [], 0 ] }
	# Measurements for publication latency requires more work because the system has to determine when new SOAs are first seen
	#   soa_first_seen keys are SOAs, values are the date first seen
	soa_first_seen = {}
	for this_rec in soa_recs:
		(this_file_prefix, this_date_time, this_rsi, this_internet, this_transport, this_dig_elapsed, this_timeout, this_soa) = this_rec
		files_seen.add(this_file_prefix)
		internet_transport_pair = this_internet + this_transport
		# Availability [gfa]
		if not this_timeout:
			rsi_availability[this_rsi][internet_transport_pair][0] += 1
		rsi_availability[this_rsi][internet_transport_pair][1] += 1
		# Response latency [fhw]
		if not this_timeout:  # [vpa]
			try:
				rsi_response_latency[this_rsi][internet_transport_pair][0].append(this_dig_elapsed)
				rsi_response_latency[this_rsi][internet_transport_pair][1] += 1
			except:
				die("Found a non-timed-out response that did not have an elapsed time: '{}'".format(this_rec))
		# Store the date that a SOA was first seen; note that this relies on soa_recs to be ordered by date_derived
		if this_soa and (not this_soa in soa_first_seen):
			soa_first_seen[this_soa] = this_date_time
	# Publication latency  # [yxn]
	#   This must be run after the soa_first_seen dict is filled in
	#   For publication latency, record the datetimes that each SOA is seen for each internet and transport pair
	#   In 
	for this_rsi in rsi_list:
		rsi_publication_latency[this_rsi] = {}
		for this_soa in soa_first_seen:
			rsi_publication_latency[this_rsi][this_soa] = { "v4udp": None, "v4tcp": None, "v6udp": None, "v6tcp": None, "last": None, "latency": None }
	# Go through the SOA records again, filling in the fields for internet and transport pairs
	#   Again, this relies on soa_recs to be in date order
	for this_rec in soa_recs:
		(this_file_prefix, this_date_time, this_rsi, this_internet, this_transport, this_dig_elapsed, this_timeout, this_soa) = this_rec
		# Timed-out responses don't count for publication latency  # [tub]
		if this_timeout:
			continue
		int_trans_pair = this_internet + this_transport
		# Store the datetimes when each SOA was seen [cnj]
		if not rsi_publication_latency[this_rsi][this_soa][int_trans_pair]:
			rsi_publication_latency[this_rsi][this_soa][int_trans_pair] = this_date_time
	# Change the "last" entry in the rsi_publication_latency to the time that the SOA was finally seen by all internet/transport pairs
	for this_rsi in rsi_list:
		for this_soa in soa_first_seen:
			for this_pair in report_pairs:
				rsi_publication_latency[this_rsi][this_soa]["last"] = rsi_publication_latency[this_rsi][this_soa][this_pair]
			# Fill in the "latency" entry by comparing the "last" to the SOA datetime; it is stored as a datetime.timedelta
			rsi_publication_latency[this_rsi][this_soa]["latency"] = rsi_publication_latency[this_rsi][this_soa]["last"] - soa_first_seen[this_soa]
				
	##############################################################

	# Get all the correctness records for this month [ebg]
	cur.execute("select file_prefix, date_derived, rsi, is_correct from public.correctness_info "\
		+ "where date_derived between '{}' and  '{}' order by date_derived".format(first_of_last_month_timestamp, end_of_last_month_timestamp))
	correctness_recs = cur.fetchall()
	log("Found {} correctness records".format(len(correctness_recs)))
	rsi_correctness = {}
	for this_rsi in rsi_list:
		# For correcness, there are two values: number of incorrect responses, and count [jof] [lbl]
		rsi_correctness[this_rsi] = [ 0, 0 ]
	for this_rec in correctness_recs:
		(this_file_prefix, this_date_time, this_rsi, this_correctness) = this_rec
		files_seen.add(this_file_prefix)
		if this_correctness:
			rsi_correctness[this_rsi][0] += 1
		rsi_correctness[this_rsi][1] += 1
		
	##############################################################

	# Note the number of measurements for this month
	report_text += "Number of measurments across all vantage points in the month: {}\n".format(len(files_seen))
	
	# Availability report
	rsi_availability_threshold = .96  # [ydw]
	report_text += "\n\nRSI Availability\nThreshold is {:.0f}%\n".format(rsi_availability_threshold * 100)  # [vmx]
	for this_rsi in rsi_list:
		report_text += "{}.root-servers.net:\n".format(this_rsi)
		for this_pair in sorted(report_pairs):
			this_ratio = rsi_availability[this_rsi][this_pair][0] / rsi_availability[this_rsi][this_pair][1]
			this_result = "Fail" if this_ratio < rsi_availability_threshold else "Pass"
			report_text += "  {}: {} ({} measurements)".format(report_pairs[this_pair], this_result, rsi_availability[this_rsi][this_pair][1])  # [lkd]
			# ratio_text = "{:.0f}".format(this_ratio)  # Only used in debugging
			# report_text += "  {}: {} ({} measurements)  {}".format(report_pairs[this_pair], this_result, rsi_availability[this_rsi][this_pair][1], ratio_text)
		report_text += "\n"
	
	# Response latency report
	rsi_response_latency_udp_threshold = 250  # [zuc]
	rsi_response_latency_tcp_threshold = 500  # [bpl]
	report_text += "\nRSI Response Latency\nThreshold for UDP is {}ms, threshold for TCP is {}ms\n"\
		.format(rsi_response_latency_udp_threshold, rsi_response_latency_tcp_threshold)  # [znh]
	for this_rsi in rsi_list:
		report_text += "{}.root-servers.net:\n".format(this_rsi)
		for this_pair in sorted(report_pairs):
			response_latency_list = sorted(rsi_response_latency[this_rsi][this_pair][0])
			response_latency_median = response_latency_list[int(rsi_response_latency[this_rsi][this_pair][1] / 2)]  # [mzx]
			if "udp" in this_pair:
				this_result = "Fail" if response_latency_median > rsi_response_latency_udp_threshold else "Pass"
			else:
				this_result = "Fail" if response_latency_median > rsi_response_latency_tcp_threshold else "Pass"
			report_text += "  {}: {} ({} measurements)".format(report_pairs[this_pair], this_result, rsi_response_latency[this_rsi][this_pair][1])  # [lxr]
			# median_text = "{}".format(response_latency_median)  # Only used in debugging
			# report_text += "  {}: {} ({} measurements)  {}".format(report_pairs[this_pair], this_result, rsi_availability[this_rsi][this_pair][1], median_text)
		report_text += "\n"
	
	# Correctness report
	rsi_correctness_threshold = 1  # [ahw]
	report_text += "\nRSI Correctness\nThreshold is 100%\n"  # [mah]
	for this_rsi in rsi_list:
		report_text += "{}.root-servers.net:\n".format(this_rsi)
		this_ratio = rsi_correctness[this_rsi][0] / rsi_correctness[this_rsi][1]  # [skm]
		this_result = "Fail" if this_ratio < rsi_correctness_threshold else "Pass"
		report_text += "  {} ({} measurements)".format(this_result, rsi_correctness[this_rsi][1])  # [fee]
		# ratio_text = "{} incorrect, {:.4f}%".format(rsi_correctness[this_rsi][1] - rsi_correctness[this_rsi][0], this_ratio)  # Only used in debugging
		# report_text += "  {} ({} measurements)  {}".format(this_result, rsi_correctness[this_rsi][1], ratio_text)
		report_text += "\n"
	
	# Publication latency report
	rsi_publication_latency_threshold = 65 # [fwa]
	report_text += "\nRSI Response Latency\nThreshold is {} minutes\n".format(rsi_publication_latency_threshold)  # [erf]
	for this_rsi in rsi_list:
		report_text += "{}.root-servers.net:\n".format(this_rsi)
		# latency_differences is the delays in publication for this letter
		latency_differences = []
		for this_soa in soa_first_seen:
			if rsi_publication_latency[this_rsi].get(this_soa):
				latency_differences.append(rsi_publication_latency[this_rsi][this_soa]["latency"].seconds)  # [kvg] [udz]
		publication_latency_median = latency_differences[int(len(latency_differences) / 2)]  # [yzp]
		this_result = "Fail" if publication_latency_median > rsi_publication_latency_threshold else "Pass"
		report_text += "  {} ({} measurements)".format(this_result, len(rsi_publication_latency[this_rsi]))
		# median_text = "{}".format(publication_latency_median)  # Only used in debugging
		# report_text += "  {} ({} measurements)  {}".format(this_result, len(rsi_publication_latency[this_rsi]), median_text)  # [jtz]
		report_text += "\n"

	##############################################################

	# Write out the report
	f_out = open(new_monthly_report_name, mode="wt")
	f_out.write(report_text)
	f_out.close()

	log("Finished report process")	
	exit()
