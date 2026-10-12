import { io } from 'socket.io-client'

function socketIOPort() {
	if (typeof window === 'undefined') {
		return '9000'
	}
	if (window.socketio_port != null && window.socketio_port !== '') {
		return String(window.socketio_port)
	}
	const boot = window.frappe?.boot
	if (boot?.socketio_port != null && boot.socketio_port !== '') {
		return String(boot.socketio_port)
	}
	const env = import.meta.env?.VITE_SOCKETIO_PORT
	if (env) {
		return String(env)
	}
	return '9000'
}

export function initSocket() {
	let host = window.location.hostname
	let siteName = window.site_name || host
	let port = window.location.port ? `:${socketIOPort()}` : ''
	let protocol = port ? 'http' : 'https'
	let url = `${protocol}://${host}${port}/${siteName}`

	let socket = io(url, {
		withCredentials: true,
		reconnectionAttempts: 5,
	})
	return socket
}
