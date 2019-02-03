# ece-diag-processor

#### Getting Started
1. Create an elasticsearch cluster
2. Add the ingest pipelines and templates:
  - pipeline.ece-proxy.json
  - pipeline.ece-services.json
  - pipeline.ece-zookeeper.json
  - template.ece.json
3. Setup filebeats keystore with the correct endpoints
  - `./filebeat keystore create`
  - `./filebeat keystore add ES_URL`
  - `./filebeat keystore add ES_USER`
  - `./filebeat keystore add ES_PASS`
4. Run filebeat from the root folder of the ECE diagnostic. It will exit when the logs have been upload.
  - `time ~/builds/beats/filebeat/filebeat-6.5.4-darwin-x86_64/filebeat -c ~/Dev/ece-diag-processor/filebeat-ece-diag.yml -e -once`


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
