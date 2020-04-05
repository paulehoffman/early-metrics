#!/usr/bin/env python3

''' Use sftp to pull from all VPs to ~/Incoming '''
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
	
	log("Started pulling")
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
	
	# Where to save the incoming files
	incoming_dir = os.path.expanduser("~/Incoming")
	if not os.path.exists(incoming_dir):
		os.mkdir(incoming_dir)

	# Get the list of VPs
	vp_list_filename = os.path.expanduser("~/vp_list.txt")
	try:
		all_vps = open(vp_list_filename, mode="rt").read().splitlines()
	except Exception as e:
		die("Could not open {} and split the lines: '{}'".format(vp_list_filename, e))

	# For each VP, find the files in /sftp/transfer/Output and get them one by one
	#   For each file, after getting, move it to /sftp/transfer/AlreadySeen
	pulled_count = 0
	for this_vp in all_vps:
		# Make a batch file for sftp that gets the directory
		dir_batch_filename = "{}/dirbatchfile.txt".format(log_dir)
		dir_f = open(dir_batch_filename, mode="wt")
		dir_f.write("cd transfer/Output\ndir -1\n")
		dir_f.close()
		# Execuite sftp with the directory batch file
		try:
			p = subprocess.run("sftp -b {} transfer@{}".format(dir_batch_filename, this_vp), shell=True, capture_output=True, text=True, check=True)
		except Exception as e:
			die("Getting directory for {} ended with '{}'".format(dir_batch_filename, e))
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
				exit("Running get for {} ended with '{}'".format(this_filename, e))
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
				exit("Running rename for {} ended with '{}'".format(this_filename, e))
			pulled_count += 1
			try:
				cur.execute("insert into files_gotten (filename_full, retrieved_at) values (%s, %s);", (this_filename, datetime.datetime.now(datetime.timezone.utc)))
			except Exception as e:
				die("Could not insert '{}' into files_gotten: '{}'".format(this_filename, e))
	log("Finished pulling; got {} files from {} VPs".format(pulled_count, len(all_vps)))
