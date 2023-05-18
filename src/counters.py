import prometheus_client

replies = prometheus_client.Counter('bot_replies', "Count of objects replied to", ['source'])
notifications = prometheus_client.Counter('bot_sent', "Count of notifications sent")
queue = prometheus_client.Gauge('bot_queue', "Current queue size")
queue_age = prometheus_client.Gauge('bot_queue_age', "Age of oldest object in queue")
objects = prometheus_client.Gauge('bot_objects', "Total number of objects by type", ['type'])
errors = prometheus_client.Counter('bot_errors', "Count of errors", ['type'])
scan_rate = prometheus_client.Summary('bot_scan_seconds', "How long it takes to scan for posts")
scan_items = prometheus_client.Counter('bot_scan_items', "Count posts scanned")
rescan_count = prometheus_client.Counter('bot_rescan_count', "Count of submissions rescanned", ['result'])
run_time = prometheus_client.Summary('bot_run_seconds', "How long a full loop takes")
sleep_time = prometheus_client.Summary('bot_sleep_seconds', "How long we sleep between loops")
api_responses = prometheus_client.Counter('bot_api_responses', "Count each type of api response", ['call', 'type'])


def init(port):
	prometheus_client.start_http_server(port)
