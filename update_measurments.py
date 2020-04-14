#!/usr/bin/env python3

''' Read files from ~/Incoming, add data to the database, move them to ~/Originals/yyyymm/ '''
# Run as the metrics user
# Run from cron job every 30 minutes
# Find records in the correctness table that have not been checked, and check them
# Reports why any failure happens

# Three-letter items in square brackets (such as [xyz]) refer to parts of rssac-047.md

import datetime, logging, os, pickle, psycopg2

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

	# Go through the files in ~/Incoming
	#   File-lever errors cause "die", record-level errors cause "alert" and skipping the record
	all_files = list(glob.glob("{}/*".format(incoming_dir)))
	for full_file in all_files:
		if not full_file.endswith(".pickle.gz"):
			vp_alert.critical("Found {} that did not end in .pickle.gz".format(full_file))
			continue
		short_file = os.path.basename(full_file).replace(".pickle.gz", "")
		# Ungz it
		try:
			with gzip.open(full_file, mode="rb") as pf:
				in_pickle = pf.read()
		except Exception as e:
			die("Could not unzip {}: '{}'".format(full_file, e))
		# Unpickle it
		try:
			in_obj = pickle.loads(in_pickle)
		except Exception as e:
			die("Could not unpickle {}: '{}'".format(full_file, e))
		# Sanity check the record
		if not ("d" in in_obj) and ("e" in in_obj) and ("r" in in_obj) and ("s" in in_obj) and ("v" in in_obj):
			die("Object in {} did not contain keys d, e, r, s, and v".format(full_file))
		# Log the metadata
		update_string = "update files_gotten set processed_at=%s, version=%s, delay=%s, elapsed=%s where filename_full=%s"
		update_vales = (datetime.datetime.now(datetime.timezone.utc), in_obj["v"], in_obj["d"], in_obj["e"], short_file+".pickle.gz") 
		try:
			cur.execute(update_string, update_vales)
		except Exception as e:
			die("Could not update {} in files_gotten: '{}'".format(short_file, e))
		# Get the derived date and VP name from the file name
		(file_date_text, file_vp) = short_file.split("-")
		try:
			file_date = datetime.datetime(int(file_date_text[0:4]), int(file_date_text[4:6]), int(file_date_text[6:8]),\
				int(file_date_text[8:10]), int(file_date_text[10:12]))
		except Exception as e:
			die("Could not split the file name '{}' into a datetime: '{}'".format(short_file, e))
		# Log the route information
		update_string = "insert into route_info (file_prefix, date_derived, vp, route_string) values (%s, %s, %s, %s)"
		update_vales = (short_file, file_date, file_vp, in_obj["s"]) 
		try:
			cur.execute(update_string, update_vales)
		except Exception as e:
			die("Could not insert into route_info for {}: '{}'".format(short_file, e))
		# Walk through the response items
		response_count = 0
		for this_resp in in_obj["r"]:
			response_count += 1
			try:
				this_resp_obj = yaml.load(this_resp[6])
			except:
				alert("Could not interpret YAML from {} of {}".format(response_count, full_file))
				continue
			# Sanity check the structure of the object
			if not this_resp_obj:
				alert("Found no object in record {} of {}".format(response_count, full_file))
				continue
			if not this_resp_obj[0].get("type"):
				alert("Found no dig type in record {} of {}".format(response_count, full_file))
				continue
			if not this_resp_obj[0].get("message"):
				alert("Found no message in record {} of {}".format(response_count, full_file))
				continue
			# Records for SOA checking
			if this_resp[4] == "S":
				# Get the this_dig_elapsed, this_timeout, this_soa for the response
				if this_resp_obj[0]["type"] == "MESSAGE":
					if (not this_resp_obj[0]["message"].get("response_time")) or (not this_resp_obj[0]["message"].get("query_time")):
						alert("Found a message without response_time or query_time in record {} of {}".format(response_count, full_file))
						continue
					dig_elapsed_as_delta = this_resp_obj[0]["message"]["response_time"] - this_resp_obj[0]["message"]["query_time"]
					this_dig_elapsed = datetime.timedelta.total_seconds(dig_elapsed_as_delta)
					this_timeout = False
					if not this_resp_obj[0]["message"].get("response_message_data").get("ANSWER_SECTION"):
						alert("Found a message without an answer in record {} of {}".format(response_count, full_file))
						continue
					this_soa_record = this_resp_obj[0]["message"]["response_message_data"]["ANSWER_SECTION"][0]
					soa_record_parts = this_soa_record.split(" ")
					this_soa = soa_record_parts[6]
				elif this_resp_obj[0]["type"] == "DIG_ERROR":
					if not (("timed out" in this_resp_obj[0]["message"]) or ("communications error" in this_resp_obj[0]["message"])):
						alert("Found unexpected dig error message '{}' in record {} of {}".format(this_resp_obj[0]["message"], response_count, full_file))
						continue
					this_dig_elapsed = None
					this_timeout = True
					this_soa = None
				else:
					alert("Found an unexpected dig type {} in record {} of {}".format(this_resp_obj[0]["type"], response_count, full_file))
					continue
				# Log the SOA information
				update_string = "insert into soa_info (file_prefix, date_derived, vp, rsi, internet, transport, prog_elapsed, dig_elapsed, timeout, soa) "\
					+ "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
				update_vales = (short_file, file_date, file_vp, this_resp[0], this_resp[1], this_resp[2], this_resp[5], this_dig_elapsed, this_timeout, this_soa) 
				try:
					cur.execute(update_string, update_vales)
				except Exception as e:
					die("Could not insert into soa_info for {}: '{}'".format(short_file, e))
			elif this_resp[4] == "C": # Records for correctness checking
				update_string = "insert into correctness_info (file_prefix, date_derived, vp, rsi, internet, transport, is_correct, failure_reason, source_pickle) "\
					+ "values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
				# Set is_correct to NULL because it will be evaluated later
				update_vales = (short_file, file_date, file_vp, this_resp[0], this_resp[1], this_resp[2], None, None, pickle.dumps(this_resp_obj))
				try:
					cur.execute(update_string, update_vales)
				except Exception as e:
					die("Could not insert into correctness_info for {}: '{}'".format(short_file, e))
			else:
				alert("Found a response type {}, which is not S or C, in record {} of {}".format(this_resp[4], response_count, full_file))
				continue
		# Move the file to ~/Originals/yyyymm
		year_from_short_file = short_file[0:4]
		month_from_short_file = short_file[4:6]
		original_dir_target = os.path.expanduser("~/Originals/{}{}".format(year_from_short_file, month_from_short_file))
		if not os.path.exists(original_dir_target):
			try:
				os.mkdir(original_dir_target)
			except Exception as e:
				die("Could not create {}: '{}'".format(original_dir_target, e))
		try:
			shutil.move(full_file, original_dir_target)
		except Exception as e:
				die("Could not move {} to {}: '{}'".format(full_file, original_dir_target, e))
	log("Finished measurements, processed {} files".format(len(all_files)))
	exit()

"""
                        Table "public.correctness_info"
     Column     |            Type             | Collation | Nullable | Default
----------------+-----------------------------+-----------+----------+---------
 file_prefix    | text                        |           |          |
 date_derived   | timestamp without time zone |           |          |
 vp             | text                        |           |          |
 rsi            | text                        |           |          |
 internet       | text                        |           |          |
 transport      | text                        |           |          |
 is_correct     | boolean                     |           |          |
 source_pickle  | bytea                       |           |          |
 failure_reason | text                        |           |          |

                         Table "public.files_gotten"
    Column     |            Type             | Collation | Nullable | Default
---------------+-----------------------------+-----------+----------+---------
 filename_full | text                        |           |          |
 retrieved_at  | timestamp without time zone |           |          |
 processed_at  | timestamp without time zone |           |          |
 version       | integer                     |           |          |
 delay         | integer                     |           |          |
 elapsed       | integer                     |           |          |

                          Table "public.route_info"
    Column    |            Type             | Collation | Nullable | Default
--------------+-----------------------------+-----------+----------+---------
 file_prefix  | text                        |           |          |
 date_derived | timestamp without time zone |           |          |
 vp           | text                        |           |          |
 route_string | text                        |           |          |

                           Table "public.soa_info"
    Column    |            Type             | Collation | Nullable | Default
--------------+-----------------------------+-----------+----------+---------
 file_prefix  | text                        |           |          |
 date_derived | timestamp without time zone |           |          |
 vp           | text                        |           |          |
 rsi          | text                        |           |          |
 internet     | text                        |           |          |
 transport    | text                        |           |          |
 prog_elapsed | real                        |           |          |
 dig_elapsed  | real                        |           |          |
 timeout      | boolean                     |           |          |
 soa          | text                        |           |          |
"""
