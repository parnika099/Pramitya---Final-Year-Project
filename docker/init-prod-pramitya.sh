#!/bin/bash
set -euo pipefail

BENCH_DIR="/home/frappe/frappe-bench"
SITE_NAME="${SITE_NAME:-pramitya.localhost}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
MARIADB_ROOT_PASSWORD="${MARIADB_ROOT_PASSWORD:-123}"

if [ "$(id -u)" = "0" ]; then
	mkdir -p "${BENCH_DIR}"
	chown -R frappe:frappe "${BENCH_DIR}"
	exec su -p -s /bin/bash frappe -c "export HOME=/home/frappe; bash /workspace/docker/init-prod-pramitya.sh"
fi

if [ -n "${NODE_VERSION_DEVELOP:-}" ] && [ -n "${NVM_DIR:-}" ]; then
	export PATH="${NVM_DIR}/versions/node/v${NODE_VERSION_DEVELOP}/bin/:${PATH}"
elif [ -n "${NODE_VERSION:-}" ] && [ -n "${NVM_DIR:-}" ]; then
	export PATH="${NVM_DIR}/versions/node/v${NODE_VERSION}/bin/:${PATH}"
fi

if [ ! -d "${BENCH_DIR}/apps/frappe" ]; then
	echo "Creating Unnati LMS bench..."
	INIT_DIR="/tmp/pramitya-frappe-bench"
	rm -rf "${INIT_DIR}"
	bench init --skip-redis-config-generation "${INIT_DIR}"
	find "${BENCH_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
	cp -a "${INIT_DIR}/." "${BENCH_DIR}/"
	rm -rf "${INIT_DIR}"
fi

cd "${BENCH_DIR}"

if ! ./env/bin/python -c "import frappe" >/dev/null 2>&1; then
	echo "Repairing Frappe editable install..."
	./env/bin/python -m pip install -q -e apps/frappe
fi

bench set-mariadb-host mariadb
bench set-redis-cache-host redis://redis:6379
bench set-redis-queue-host redis://redis:6379
bench set-redis-socketio-host redis://redis:6379

sed -i '/redis/d' ./Procfile || true
sed -i '/watch/d' ./Procfile || true

ensure_python_app() {
	local app="$1"
	local module="$2"
	if [ -d "apps/${app}" ] && ! ./env/bin/python -c "import ${module}" >/dev/null 2>&1; then
		echo "Repairing ${app} editable install..."
		./env/bin/python -m pip install -q -e "apps/${app}"
	fi
}

ensure_bench_app() {
	local app="$1"
	sed -i 's/paymentslms/payments\nlms/g' sites/apps.txt
	if [ -s sites/apps.txt ] && [ "$(tail -c 1 sites/apps.txt | wc -l)" -eq 0 ]; then
		printf '\n' >> sites/apps.txt
	fi
	awk 'NF && !seen[$0]++' sites/apps.txt > sites/apps.txt.tmp
	mv sites/apps.txt.tmp sites/apps.txt
	if ! grep -qx "${app}" sites/apps.txt; then
		printf '%s\n' "${app}" >> sites/apps.txt
	fi
}

if [ ! -d "apps/payments" ]; then
	bench get-app payments
fi
ensure_python_app payments payments
ensure_bench_app payments

if [ ! -e "apps/lms" ]; then
	ln -s /workspace apps/lms
fi
ensure_python_app lms lms
ensure_bench_app lms

echo "Installing frontend dependencies..."
(cd /workspace/frontend && yarn install --check-files)

if [ ! -d "sites/${SITE_NAME}" ]; then
	bench new-site "${SITE_NAME}" \
		--mariadb-root-password "${MARIADB_ROOT_PASSWORD}" \
		--admin-password "${ADMIN_PASSWORD}" \
		--no-mariadb-socket
fi

install_app_if_missing() {
	local app="$1"
	if ! bench --site "${SITE_NAME}" list-apps | grep -qx "${app}"; then
		bench --site "${SITE_NAME}" install-app "${app}"
	fi
}

install_app_if_missing payments
install_app_if_missing lms

bench --site "${SITE_NAME}" set-config developer_mode 0
bench --site "${SITE_NAME}" set-config host_name "https://${SITE_NAME}"
bench --site "${SITE_NAME}" execute frappe.db.set_single_value --args '["System Settings", "app_name", "Unnati Development LMS"]'

if [ -n "${DEEPGRAM_API_KEY:-}" ]; then
	bench --site "${SITE_NAME}" set-config deepgram_api_key "${DEEPGRAM_API_KEY}"
fi
if [ -n "${DEEPGRAM_AGENT_WS_URL:-}" ]; then
	bench --site "${SITE_NAME}" set-config deepgram_agent_ws_url "${DEEPGRAM_AGENT_WS_URL}"
fi
if [ -n "${DEEPGRAM_THINK_PROVIDER:-}" ]; then
	bench --site "${SITE_NAME}" set-config deepgram_think_provider "${DEEPGRAM_THINK_PROVIDER}"
fi
if [ -n "${DEEPGRAM_THINK_MODEL:-}" ]; then
	bench --site "${SITE_NAME}" set-config deepgram_think_model "${DEEPGRAM_THINK_MODEL}"
fi
if [ -n "${DEEPGRAM_LISTEN_MODEL:-}" ]; then
	bench --site "${SITE_NAME}" set-config deepgram_listen_model "${DEEPGRAM_LISTEN_MODEL}"
fi
if [ -n "${DEEPGRAM_SPEAK_MODEL:-}" ]; then
	bench --site "${SITE_NAME}" set-config deepgram_speak_model "${DEEPGRAM_SPEAK_MODEL}"
fi

bench --site "${SITE_NAME}" migrate
bench build --app lms
bench --site "${SITE_NAME}" execute lms.demo.demo_data.create_showcase_demo_data
bench --site "${SITE_NAME}" execute frappe.db.set_single_value --args '["System Settings", "app_name", "Unnati Development LMS"]'
bench --site "${SITE_NAME}" execute frappe.db.set_single_value --args '["Website Settings", "app_name", "Unnati Development LMS"]'
bench --site "${SITE_NAME}" clear-cache
bench use "${SITE_NAME}"

exec bench start
