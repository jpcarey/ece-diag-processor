# ece-diag-processor

#### Getting Started
1. Clone this repository to an appropriate location (eg `~/Dev`)
2. You will need a working python3 environment with `pip3 install requests`
3. cd into this cloned repository, and use `go build decrypt_keystore`
  - This assumes that you have a working golang environment
  - You may need to Go Get the necessary dependencies (eg. `go get -u golang.org/x/crypto/pbkdf2`)
4. Create an elasticsearch cluster (Elastic Cloud...)
5. export FB_PATH, this should point to your filebeat executable. The script will prompt for this value if not set.
6. Setup filebeat's keystore with the correct endpoints
  - `./filebeat keystore create`
  - `./filebeat keystore add ES_URL`
  - `./filebeat keystore add ES_USER`
  - `./filebeat keystore add ES_PASS`
7. From the root folder of the ECE diagnostic, run `python3 ~/Dev/ece-diag-processor/ECE_diag_processor.py`.

This is a work in progress.

Tested with filebeat-6.5.4 and Elastic Cloud / 6.6.0 elasticsearch cluster.

#### TODO items
1. ~~Rename `metadata` -> `@metadata`. This would display nicer in Kibana Discover (due to the key sorting)~~
2. ~~`metadata.file` does not need to include the diagnostic name. This has already been extracted to `metadata.diag_name`~~
3. Proxy Logs Mapping (done, add lowercasing and path analyzers)
4. Elasticsearch Logs Mapping
5. Services Logs Mapping
6. Verify Timezones are properly handled for logs
7. Missing logs and data:
  - Kibana is missing the bootlog.
  - Need to simplify picking up all files. Maybe some conditionals in the ingest pipeline, and unknown files could be dumped to catchall index.
8. Some data may require preprocessing (system commands / docker container logs / inspect json)
  - Older version of the diagnostic did not have the same folder structure. Need to evaluate if this could be corrected easily. Also need to handle json logging formats.
  - I'm considering a custom beat, which would allow the preprocessing & logic. This would allow prompting for credentials and automatically creating the destination cluster (and configuring) in Elastic Cloud. Idea would be to print the relevant information to the console, and provide a console based progress bar. Could potentially write the progress data to elasticsearch as well, but need to evaluate how to conditionally display the uploading status in Kibana.
9. Dashboards and Visualizations
10. Find common issues in the data (run watcher?)
