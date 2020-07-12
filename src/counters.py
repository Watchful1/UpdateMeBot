import prometheus_client

replies = prometheus_client.Counter('bot_replies', "Count of objects replied to", ['source'])
notifications = prometheus_client.Counter('bot_sent', "Count of notifications sent")
queue = prometheus_client.Gauge('bot_queue', "Current queue size")
objects = prometheus_client.Gauge('bot_objects', "Total number of active subscriptions")
errors = prometheus_client.Counter('bot_errors', "Count of errors", ['type'])
scan_rate = prometheus_client.Summary('bot_scan_seconds', "Count posts scanned")
scan_items = prometheus_client.Counter('bot_scan_items', "Count posts scanned")


def init(port):
	prometheus_client.start_http_server(port)
