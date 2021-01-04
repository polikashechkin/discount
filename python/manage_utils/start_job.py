import redis
r = redis.StrictRedis(host='localhost', port=6379)
#r.publish('job:start', '{"proc":"test.py", "module":"domino", "account":"00674812"}')
#r.publish('job:start', '{"JOB_ID":499}')
r.publish('job:start', '{"ID":8}')
r.publish('job:start', '{"ID":8}')
r.publish('job:start', '{"ID":8}')
r.publish('job:start', '{"ID":8}')
r.publish('job:start', '{"ID":8}')
#r.publish('job:check', '{}')

