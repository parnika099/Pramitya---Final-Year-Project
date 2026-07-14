export const SEMESTERS = [
	'Semester 1',
	'Semester 2',
	'Semester 3',
	'Semester 4',
	'Semester 5',
	'Semester 6',
	'Semester 7',
	'Semester 8',
	'Year 1',
	'Year 2',
	'Year 3',
	'Year 4',
]

export const PAYMENT_METHODS = [
	'Cash',
	'UPI',
	'Card',
	'Bank Transfer',
	'Cheque',
	'Other',
]

export const FEE_STATUSES = ['Paid', 'Partially Paid', 'Pending', 'Overdue']

export function validateMoney(value, allowZero = true) {
	const text = String(value ?? '').trim()
	if (!text) return 'Amount is required'
	if (!/^\d+(\.\d{1,2})?$/.test(text)) {
		return 'Enter a valid amount with up to 2 decimal places'
	}
	if (!allowZero && Number(text) === 0) {
		return 'Amount must be greater than zero'
	}
	return ''
}

export function errorMessage(error) {
	return error?.messages?.[0] || error?.message || 'Something went wrong'
}

export function statusTheme(status) {
	if (status === 'Paid') return 'green'
	if (status === 'Partially Paid') return 'orange'
	if (status === 'Overdue') return 'red'
	return 'gray'
}

export function downloadTextFile(filename, content, mime = 'text/csv;charset=utf-8') {
	const blob = new Blob([content], { type: mime })
	const url = URL.createObjectURL(blob)
	const link = document.createElement('a')
	link.href = url
	link.download = filename
	link.click()
	URL.revokeObjectURL(url)
}

function escapeHtml(value) {
	return String(value ?? '')
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
}

export function printTable(title, columns, rows) {
	const popup = window.open('', '_blank', 'noopener,noreferrer')
	if (!popup) return
	const head = columns
		.map((column) => `<th>${escapeHtml(column.label)}</th>`)
		.join('')
	const body = rows
		.map(
			(row) =>
				`<tr>${columns
					.map((column) => `<td>${escapeHtml(row[column.key] ?? '')}</td>`)
					.join('')}</tr>`
		)
		.join('')
	popup.document.write(`<!doctype html>
		<html>
			<head>
				<title>${escapeHtml(title)}</title>
				<style>
					body { font-family: sans-serif; color: #1c2454; margin: 24px; }
					h1 { font-size: 20px; }
					table { border-collapse: collapse; width: 100%; }
					th, td { border: 1px solid #dce1ef; padding: 6px 8px; text-align: left; font-size: 12px; }
					th { background: #f3f5fa; }
				</style>
			</head>
			<body>
				<h1>${escapeHtml(title)}</h1>
				<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>
			</body>
		</html>`)
	popup.document.close()
	popup.focus()
	popup.print()
}
