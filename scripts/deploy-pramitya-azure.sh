#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RG="${AZURE_RESOURCE_GROUP:-pramitya-rg}"
LOCATION="${AZURE_LOCATION:-centralindia}"
VM_NAME="${AZURE_VM_NAME:-pramitya-vm}"
VM_SIZE="${AZURE_VM_SIZE:-Standard_B1ms}"
ADMIN_USER="${AZURE_ADMIN_USER:-azureuser}"
DNS_LABEL="${AZURE_DNS_LABEL:-pramitya}"
DOMAIN_NAME="${PRAMITYA_DOMAIN:-}"
DEPLOY_ROOT="${PRAMITYA_DEPLOY_ROOT:-/opt/pramitya}"
APP_DIR="${DEPLOY_ROOT}/lms"

if [ -n "${DOMAIN_NAME}" ]; then
	SITE_NAME="${PRAMITYA_SITE_NAME:-pramitya.${DOMAIN_NAME}}"
else
	SITE_NAME="${PRAMITYA_SITE_NAME:-${DNS_LABEL}.${LOCATION}.cloudapp.azure.com}"
fi

command -v az >/dev/null
command -v rsync >/dev/null
command -v ssh >/dev/null

az account show >/dev/null
if ! az group show --name "${RG}" >/dev/null 2>&1; then
	az group create --name "${RG}" --location "${LOCATION}" >/dev/null
fi

if ! az vm show --resource-group "${RG}" --name "${VM_NAME}" >/dev/null 2>&1; then
	echo "Creating VM ${VM_NAME} (${VM_SIZE}) in ${LOCATION}..."
	CREATE_ERR="$(mktemp)"
	if ! az vm create \
		--resource-group "${RG}" \
		--name "${VM_NAME}" \
		--location "${LOCATION}" \
		--image Ubuntu2404 \
		--size "${VM_SIZE}" \
		--admin-username "${ADMIN_USER}" \
		--generate-ssh-keys \
		--public-ip-address-dns-name "${DNS_LABEL}" \
		--storage-sku Standard_LRS \
		--os-disk-size-gb 30 \
		--output none 2> >(tee "${CREATE_ERR}" >&2); then
		if grep -qi "SkuNotAvailable\\|Capacity Restrictions" "${CREATE_ERR}"; then
			echo "VM size ${VM_SIZE} is not available in ${LOCATION}. Try AZURE_LOCATION=eastus or AZURE_VM_SIZE=Standard_B2s." >&2
			rm -f "${CREATE_ERR}"
			exit 2
		fi
		if grep -Eqi "dns|domain label|already.*use|DnsRecord" "${CREATE_ERR}" && [ -z "${AZURE_DNS_LABEL:-}" ] && [ -z "${DOMAIN_NAME}" ]; then
			DNS_LABEL="pramitya-${RANDOM}"
			SITE_NAME="${DNS_LABEL}.${LOCATION}.cloudapp.azure.com"
			echo "DNS label pramitya was unavailable; retrying with ${DNS_LABEL}..."
			az vm create \
				--resource-group "${RG}" \
				--name "${VM_NAME}" \
				--location "${LOCATION}" \
				--image Ubuntu2404 \
				--size "${VM_SIZE}" \
				--admin-username "${ADMIN_USER}" \
				--generate-ssh-keys \
				--public-ip-address-dns-name "${DNS_LABEL}" \
				--storage-sku Standard_LRS \
				--os-disk-size-gb 30 \
				--output none
		else
			rm -f "${CREATE_ERR}"
			exit 1
		fi
	fi
	rm -f "${CREATE_ERR}"
fi

PUBLIC_IP="$(az vm show -d --resource-group "${RG}" --name "${VM_NAME}" --query publicIps -o tsv)"
FQDN="$(az vm show -d --resource-group "${RG}" --name "${VM_NAME}" --query fqdns -o tsv)"
if [ -z "${FQDN}" ]; then
	FQDN="${PUBLIC_IP}"
fi
if [ -z "${DOMAIN_NAME}" ] && [ -z "${PRAMITYA_SITE_NAME:-}" ] && [[ "${FQDN}" == *.cloudapp.azure.com ]]; then
	SITE_NAME="${FQDN}"
fi

NIC_ID="$(az vm show --resource-group "${RG}" --name "${VM_NAME}" --query 'networkProfile.networkInterfaces[0].id' -o tsv)"
NSG_ID="$(az network nic show --ids "${NIC_ID}" --query 'networkSecurityGroup.id' -o tsv)"
NSG_NAME="$(basename "${NSG_ID}")"

ADMIN_IP="$(curl -fsS https://api.ipify.org || true)"
az network nsg rule create --resource-group "${RG}" --nsg-name "${NSG_NAME}" \
	--name AllowHTTP --priority 100 --direction Inbound --access Allow --protocol Tcp \
	--source-address-prefixes '*' --source-port-ranges '*' --destination-address-prefixes '*' \
	--destination-port-ranges 80 --output none || true
az network nsg rule create --resource-group "${RG}" --nsg-name "${NSG_NAME}" \
	--name AllowHTTPS --priority 110 --direction Inbound --access Allow --protocol Tcp \
	--source-address-prefixes '*' --source-port-ranges '*' --destination-address-prefixes '*' \
	--destination-port-ranges 443 --output none || true
if [ -n "${ADMIN_IP}" ]; then
	az network nsg rule delete --resource-group "${RG}" --nsg-name "${NSG_NAME}" --name default-allow-ssh >/dev/null 2>&1 || true
	az network nsg rule create --resource-group "${RG}" --nsg-name "${NSG_NAME}" \
		--name AllowSSHAdmin --priority 1000 --direction Inbound --access Allow --protocol Tcp \
		--source-address-prefixes "${ADMIN_IP}/32" --source-port-ranges '*' --destination-address-prefixes '*' \
		--destination-port-ranges 22 --output none || true
fi

if [ -n "${DOMAIN_NAME}" ]; then
	az network dns zone create --resource-group "${RG}" --name "${DOMAIN_NAME}" >/dev/null
	az network dns record-set a create --resource-group "${RG}" --zone-name "${DOMAIN_NAME}" --name pramitya >/dev/null
	az network dns record-set a add-record --resource-group "${RG}" --zone-name "${DOMAIN_NAME}" \
		--record-set-name pramitya --ipv4-address "${PUBLIC_IP}" >/dev/null || true
	echo "Azure DNS nameservers:"
	az network dns zone show --resource-group "${RG}" --name "${DOMAIN_NAME}" --query nameServers -o tsv
fi

echo "Waiting for SSH on ${FQDN}..."
for _ in $(seq 1 60); do
	if ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 "${ADMIN_USER}@${FQDN}" true 2>/dev/null; then
		break
	fi
	sleep 5
done

ssh "${ADMIN_USER}@${FQDN}" "sudo mkdir -p '${DEPLOY_ROOT}' && sudo chown -R '${ADMIN_USER}:${ADMIN_USER}' '${DEPLOY_ROOT}'"

rsync -az --delete \
	--exclude '.git' \
	--exclude 'node_modules' \
	--exclude 'frappe-ui' \
	--exclude 'lms/public/frontend' \
	--exclude 'lms/www/_lms.html' \
	--exclude '*.pyc' \
	--exclude '__pycache__' \
	"${REPO_ROOT}/" "${ADMIN_USER}@${FQDN}:${APP_DIR}/"

REMOTE_ENV_CMD=$(cat <<EOF
set -euo pipefail
cd '${APP_DIR}'
touch docker/.env
grep -q '^SITE_NAME=' docker/.env || echo 'SITE_NAME=${SITE_NAME}' >> docker/.env
grep -q '^MARIADB_ROOT_PASSWORD=' docker/.env || echo "MARIADB_ROOT_PASSWORD=\$(openssl rand -hex 18)" >> docker/.env
grep -q '^ADMIN_PASSWORD=' docker/.env || echo "ADMIN_PASSWORD=\$(openssl rand -base64 24 | tr -d '=+/')" >> docker/.env
grep -q '^DEMO_PASSWORD=' docker/.env || echo "DEMO_PASSWORD=\$(openssl rand -base64 18 | tr -d '=+/')" >> docker/.env
if ! grep -q '^DEEPGRAM_API_KEY=' docker/.env; then
	echo 'DEEPGRAM_API_KEY=' >> docker/.env
fi
chmod 600 docker/.env
EOF
)
ssh "${ADMIN_USER}@${FQDN}" "${REMOTE_ENV_CMD}"

ssh "${ADMIN_USER}@${FQDN}" "if ! command -v docker >/dev/null; then
	sudo apt-get update
	sudo apt-get install -y ca-certificates curl gnupg rsync openssl
	sudo install -m 0755 -d /etc/apt/keyrings
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
	sudo chmod a+r /etc/apt/keyrings/docker.gpg
	echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \$(. /etc/os-release && echo \$VERSION_CODENAME) stable\" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
	sudo apt-get update
	sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
	sudo usermod -aG docker '${ADMIN_USER}'
fi
if [ ! -f /swapfile ]; then
	sudo fallocate -l 4G /swapfile
	sudo chmod 600 /swapfile
	sudo mkswap /swapfile
	echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
	sudo swapon /swapfile
fi"

ssh "${ADMIN_USER}@${FQDN}" "cd '${APP_DIR}' && sudo docker compose --env-file docker/.env -f docker/docker-compose.pramitya.yml up -d"

echo "Pramitya deployment started."
echo "URL: https://${SITE_NAME}/lms"
echo "SSH: ssh ${ADMIN_USER}@${FQDN}"
echo "Credentials file on VM: ${APP_DIR}/docker/.env"
