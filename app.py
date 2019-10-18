from celery import Celery
from kafka import KafkaProducer
from collections import OrderedDict
import subprocess
import config
import logging
import json

app = Celery('app', broker="redis://{}:6379".format(config.REDIS_HOST))

@app.task
def submit_flink_sql(definition):
    logging.info(definition)
    process = subprocess.Popen(['./docker-entrypoint.sh', 'python3', 'sql.py', definition], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    definition = json.loads(definition)
    feedback = {
	"id": definition["id"],
        "success": bool(stderr)
    }

    logging.info(stdout.decode('utf-8'))
    if stderr:
        feedback["error"] = stderr.decode('utf-8)
        logging.error(stderr.decode('utf-8'))
    else:
        feedback["jobId"] = stdout.decode('utf-8')

    producer = KafkaProducer(bootstrap_servers=config.BOOTSTRAP_SERVERS)
    future = producer.send("{}.{}.feedback".format(definition["projectId"], definition["pipelineId"]), json.dumps(feedback).encode('utf-8'))
    result = future.get(timeout=10)

    return (stdout, stderr)

