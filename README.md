Matching timetabled bus journeys to archived real-time bus trips
================================================================

The scripts in this repository attempt to match real-time bus position information against timetabled journeys and to present the results as a table from which trips and journeys can be viewed on a map.

This document provides instructions for installing them on the TFC platform. See [DESCRIPTION.md](DESCRIPTION.md) for a more general description and instructions for a stand-alone installation.

Installation
============

1. Clone this repository in the home directory of the `tfc_prod` user

2. `cd timetable_matching`

2. `mkdir -p /mnt/sdb1/tfc/cam_tt_matching/json`

3. `mkdir -p /mnt/sdb1/tfc/tnds/sections`

4. `ln -s /mnt/sdb1/tfc/cam_tt_matching/ /media/tfc/cam_tt_matching`

5. `ln -s /mnt/sdb1/tfc/tnds/ /media/tfc/tnds`

6. (as root) `cp nginx/tt_matching.conf /etc/nginx/includes2/`

7. (as root) `service nginx restart`

8. `python3 -m venv venv`

9. `pip install -r requirements.txt`

10. `cp setup_environment.skel setup_environment`. Edit `setup_environment` to set at least `API_TOKEN`, `TNDS_USERNAME` and `TNDS_PASSWORD` (or copy from one of the other servers). The default values of the other variables should be fine.

The script `refresh_timetable.sh` will fetch a copy of the requred timetable files into `/media/tfc/tnds`. It runs no more than once every 2 hours and only fetched timetable data when it changes.

The script `process_day.sh` (which itself runs `refresh_timetable.sh`) takes zero or more 'YYYY-MM-DD' command-line parameters and generates merged data files for the corresponding days. If run with no command-line parameters it generates merged data files for "yesterday". It shouldn't be run for a day that doesn't have complete trip data (like 'today').

On `tfc-app4`, `tfc_prod`'s crontab file has run `process_day.sh` daily at 02:45 since late September 2018:

```
# Extract yesterday's timetable and journeys
45 2 * * * cd /home/tfc_prod/timetable_matching/ && ./process_day.sh >/var/log/tfc_prod/process_day.err 2>&1 && echo $(date --iso-8601=seconds) > /var/log/tfc_prod/process_day.timestamp
```

The web interface for interrogating the analysed data is at `http://<hostname>/backdoor/tt_matching/index.html`. It needs to be run with a query parameter identifying the day to analyse, e.g.

    http://<hostname>/backdoor/tt_matching/index.html?2018-10-01
