window.addEventListener('load', () => {
	const form = document.messagebox;
	form.addEventListener('submit', (event) => {
		event.preventDefault();
		const submitButton = document.getElementById('submitButton');
		submitButton.disabled = true;
		const data = new FormData(form);
		fetch(window.location.href, {method: 'POST', body: data}).then(async (resp) => {
			if (resp.ok) {
				window.location.reload();
			} else {
				alert(await resp.text());
			}
			submitButton.disabled = false;
		});
	});
});