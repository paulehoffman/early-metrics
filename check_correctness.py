#!/usr/bin/env python3

''' Find records in the correctness table that have not been checked, and check them '''
# Run as the metrics user
# Run from cron job every 30 minutes
# Reports why any failure happens

# Three-letter items in square brackets (such as [xyz]) refer to parts of rssac-047.md

import datetime, logging, psycopg2, subprocess

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
	
	log("Started correctness checking")
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
	
	checked_count = 0
	cur.execute("select (id, source_pickle) from correctness_info where is_correct is null")
	for this_record in cur:
		(this_id, this_source) = this_record
		####### Determine correctness (boolean) and failure_text
		############# cur.execute("update correctness_info set (is_correct, failure_reason) = (%s, %s) where id = this_id", (correctness, failure_text))
		checked_count += 1
	
	log("Finished correctness checking, processed {} records".format(checked_count))
	exit()

"""
                        Table "public.correctness_info"
     Column     |            Type             | Collation | Nullable | Default
----------------+-----------------------------+-----------+----------+---------
 id             | integer                     |           | not null | generated always as identity
 file_prefix    | text                        |           |          |
 date_derived   | timestamp without time zone |           |          |
 vp             | text                        |           |          |
 rsi            | text                        |           |          |
 internet       | text                        |           |          |
 transport      | text                        |           |          |
 is_correct     | boolean                     |           |          |
 source_pickle  | bytea                       |           |          |
 failure_reason | text                        |           |          |

"""
