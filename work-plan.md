# Metrics Work Plan

- Use mtric.net as domain name for RSSAC work
- Each vantage point (VP) is named `nnn`.mtric.net where `nnn` is a three-digit number
- Collector is named c00.mtric.net

## Deployment

- Deployed with Ansible
	- In `Ansible` directory in the repo
	- Files that are not part of the distribution are on `Local` directory in the repo
	- Create VPs first with `vps_building.yml`, then create collector with `collector_building.yml`
	- Creates users on collector with names transfer-xxx to receive files from the VPs

## Logging and alerts

- Logs are text files kept on VPs and collector
- Alerts are text files, monitored by Prometheus on collector
	- ~/Logs/nnn-alerts.txt on every machine
- All Python scripts have _die_ function that prints to alert logs

## Vantage points

- Each VP should have more than one core if possible

- `vantage_point_metrics.py`
	- Is run from cron job every 5 minutes on 0, 5, ... `[wyn]` `[mba]` `[wca]`
	- Use `dig + yaml` from BIND 9.16
	- Run `scamper` after queries to each source for both IPv4 and IPv6
	- Results of each run are saved as .pickle.gz to ~/Output
	- Also pushed to collector during run
	- Logs to ~/Logs/nnn-log.txt

- `watch_fp.py`
	- Run from cron every 5 minutes on 4, 9, ...
	- Alerts if no output from most recent run
	- Check for disk usage > 80%, alert if found

- Distribution of vantage points
	- Remind RSSAC Caucus of the previous discussion
	- Spin up a VM in every data center for North America, Asia, and Europe
	- Do traceroutes to two places
	- Ask if they need more or, if not, which to use

- Maintenance
	- Be sure NTP is updating properly  `[ugt]`
	
- Possible VP providers
	- hertzner.com
	- Linode
	- Digital Ocean
	- AWS
	- Google Cloud
	- OVH
	- Vultr.com
	- Ask the GSEs for others


## Collector

- Run on a VM with lots of cores and memory
- All programs run as metrics user

- `get_root_zone.py`
	- Stores zones in ~/Output/RootZones
	- Run from cron job every 30 minutes
	- Process zone file with BIND utility, look for SOA
	- If not already there, name new file _soa_.root.txt

- `update_measurments.py`
	- Run from cron job every 5 minutes on 4, 9, ...
	- For each .gz file in /sftp/transfer-nnn
		- Open file, store results in the database
		- Move file to ~/Originals/yyyymm/

- `produce_reports.py`
	- Run from cron job every week, and on the first of each month
	-`--style _n_` to say what style of report (weekly, monthly)

- `watch_collector.py`
	- Run from cron job every 30 minutes on 1, 31
	- Alerts if ~/Output/Originals is not fuller than on the last run
	- Alerts if ~/Output/root_zones is not fuller than it was 24 hours ago
	- Check for disk usage > 80%, alert if found

- Data distribution
	- Raw responses (.pickle.gz) files available for a month or longer
	- Available by read-only rsync or maybe HTTPS
