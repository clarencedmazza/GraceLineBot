# tasks.py

import os
from redis import Redis
from rq import Queue
from main import generate_devotional

r = Redis.from_url(os.getenv("REDIS_URL"))
q = Queue(connection=r)

def queue_devotional(chat_id):
    q.enqueue(generate_devotional, chat_id)
