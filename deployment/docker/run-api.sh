#!/usr/bin/env bash

docker run -d -p 8001:8000 -e MONGODB_URL=mongodb://172.17.42.1:27017/windmobile -e SENTRY_DSN={SENTRY_DSN} \
-e ENVIRONMENT=production -e OPENAPI_PREFIX=/api/2.1 --restart=always --name=winds-mobi-api windsmobi/winds-mobi-api
