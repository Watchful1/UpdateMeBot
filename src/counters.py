import prometheus_client

replies = prometheus_client.Counter('bot_replies', "Count of objects replied to", ['source'])
notifications = prometheus_client.Counter('bot_sent', "Count of notifications sent")
queue = prometheus_client.Gauge('bot_queue', "Current queue size")
objects = prometheus_client.Gauge('bot_objects', "Total number of active subscriptions")
errors = prometheus_client.Counter('bot_errors', "Count of errors", ['type'])
scan_rate = prometheus_client.Summary('bot_scan_seconds', "How long it takes to scan for posts")
scan_items = prometheus_client.Counter('bot_scan_items', "Count posts scanned")
pushshift_delay = prometheus_client.Gauge('bot_pushshift_minutes', "Pushshift delay in minutes", ['client'])
pushshift_failed = prometheus_client.Gauge('bot_pushshift_failed', "Pushshift timeout status", ['client'])
pushshift_client = prometheus_client.Gauge('bot_pushshift_client', "Which pushshift client is being used", ['client'])
rescan_queue = prometheus_client.Gauge('bot_rescan_queue', "Current rescan queue size")
rescan_count = prometheus_client.Counter('bot_rescan_count', "Count of submissions rescanned", ['result'])
run_time = prometheus_client.Summary('bot_run_seconds', "How long a full loop takes")
sleet_time = prometheus_client.Summary('bot_sleep_seconds', "How long we sleep between loops")


def init(port):
	prometheus_client.start_http_server(port)
