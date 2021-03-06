import os
import redis
from rq import Worker, Queue, Connection

listen = ['default']

redis_url = os.getenv('REDIS_URL',
                      'redis://localhost:6379').strip().replace('"', '')

print(f'redis url: {redis_url}')

if __name__ == '__main__':
    with Connection(redis.from_url(redis_url)):
        worker = Worker(list(map(Queue, listen)))
        worker.work()
