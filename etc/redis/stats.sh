redis-cli KEYS "alt/*" | wc -l

redis-cli KEYS "alt/*" | xargs -L 1 -I key redis-cli hget key is_peak

redis-cli KEYS "alt/*" | xargs -L 1 -I key redis-cli ttl key | awk '$1<86400' | wc -l
