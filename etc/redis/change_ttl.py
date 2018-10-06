import redis


def main():
    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    for key in r.scan_iter('alt/*'):
        ttl = r.ttl(key)
        r.expire(key, ttl * 2)


if __name__ == '__main__':
    main()
