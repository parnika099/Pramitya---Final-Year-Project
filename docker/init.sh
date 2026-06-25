#!bin/bash

if [ -d "/home/frappe/frappe-bench/apps/frappe" ]; then
    echo "Bench already exists, skipping init"
    cd frappe-bench
    bench start
else
    echo "Creating new bench..."
fi

export PATH="${NVM_DIR}/versions/node/v${NODE_VERSION_DEVELOP}/bin/:${PATH}"

bench init --skip-redis-config-generation frappe-bench

cd frappe-bench

# Use containers instead of localhost
bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

# Remove redis, watch from Procfile
sed -i '/redis/d' ./Procfile
sed -i '/watch/d' ./Procfile

bench get-app payments
bench get-app lms

bench new-site lms.localhost \
--force \
--mariadb-root-password 123 \
--admin-password admin \
--no-mariadb-socket

bench --site lms.localhost install-app payments
bench --site lms.localhost install-app lms
bench --site lms.localhost set-config developer_mode 1
if [ -n "${DEEPGRAM_API_KEY:-}" ]; then
	bench --site lms.localhost set-config deepgram_api_key "${DEEPGRAM_API_KEY}"
fi
if [ -n "${DEEPGRAM_THINK_PROVIDER:-}" ]; then
	bench --site lms.localhost set-config deepgram_think_provider "${DEEPGRAM_THINK_PROVIDER}"
fi
if [ -n "${DEEPGRAM_THINK_MODEL:-}" ]; then
	bench --site lms.localhost set-config deepgram_think_model "${DEEPGRAM_THINK_MODEL}"
fi
if [ -n "${DEEPGRAM_LISTEN_MODEL:-}" ]; then
	bench --site lms.localhost set-config deepgram_listen_model "${DEEPGRAM_LISTEN_MODEL}"
fi
if [ -n "${DEEPGRAM_SPEAK_MODEL:-}" ]; then
	bench --site lms.localhost set-config deepgram_speak_model "${DEEPGRAM_SPEAK_MODEL}"
fi
bench --site lms.localhost clear-cache
bench use lms.localhost

bench start
