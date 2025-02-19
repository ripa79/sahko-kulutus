document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('settingsForm');
    const messageDiv = document.getElementById('settingsMessage');
    let storedUsername = ''; // store fetched username
    let storedYear = ''; // store fetched year
    let storedSpotMargin = ''; // store fetched spot margin
    
    // Fetch current settings to pre-fill the form (excluding password)
    try {
        const res = await fetch('/api/settings');
        if (!res.ok) throw new Error('Failed to load settings.');
        const { settings } = await res.json();
        storedUsername = settings.ELENIA_USERNAME;
        storedYear = settings.YEAR;
        storedSpotMargin = settings.SPOT_MARGIN;
        form.elements['ELENIA_USERNAME'].value = storedUsername;
        form.elements['YEAR'].value = storedYear;
        form.elements['SPOT_MARGIN'].value = storedSpotMargin;
    } catch (error) {
        messageDiv.innerHTML = `<p style="color: red">Error: ${error.message}</p>`;
    }
    
    // Helper function to submit settings update
    const submitSettings = async () => {
        messageDiv.innerHTML = '';
        const data = {
            YEAR: form.elements['YEAR'].value.trim(),
            SPOT_MARGIN: form.elements['SPOT_MARGIN'].value.trim(),
            ELENIA_USERNAME: document.getElementById('updateCredentialsCheck').checked
                              ? form.elements['ELENIA_USERNAME'].value.trim()
                              : storedUsername
        };
        if (document.getElementById('updateCredentialsCheck').checked) {
            data.ELENIA_PASSWORD = form.elements['ELENIA_PASSWORD'].value;
            data.ELENIA_PASSWORD_CONFIRM = form.elements['ELENIA_PASSWORD_CONFIRM'].value;
            if (data.ELENIA_PASSWORD !== data.ELENIA_PASSWORD_CONFIRM) {
                messageDiv.innerHTML = `<p style="color: red">Passwords do not match.</p>`;
                return;
            }
        }
        try {
            const res = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (!res.ok) throw new Error(result.error || 'Failed to update settings.');
            messageDiv.innerHTML = `<p style="color: green">${result.message}</p>`;
            form.elements['ELENIA_PASSWORD'].value = '';
            form.elements['ELENIA_PASSWORD_CONFIRM'].value = '';
            
            // Trigger data update if YEAR or SPOT_MARGIN has changed
            if (form.elements['YEAR'].value.trim() !== storedYear ||
                form.elements['SPOT_MARGIN'].value.trim() !== storedSpotMargin) {
                try {
                    const updateRes = await fetch('/api/update', { method: 'POST' });
                    if (!updateRes.ok) throw new Error('Failed to trigger data update.');
                    messageDiv.innerHTML += `<p style="color: green">Data update triggered.</p>`;
                    // Update stored values after successful update trigger
                    storedYear = form.elements['YEAR'].value.trim();
                    storedSpotMargin = form.elements['SPOT_MARGIN'].value.trim();
                } catch (err) {
                    messageDiv.innerHTML += `<p style="color: orange">Warning: ${err.message}</p>`;
                }
            }
            // After successful update, redirect back
            messageDiv.innerHTML += `<p style="color: green">Redirecting back...</p>`;
            setTimeout(() => {
                window.location.href = document.referrer || '/';
            }, 2000);
        } catch (error) {
            messageDiv.innerHTML = `<p style="color: red">Error: ${error.message}</p>`;
        }
    };

    // Handle form submission (update triggered by "Update Settings" button)
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await submitSettings();
    });
    
    // Toggle credentials fields using the correct checkbox and container
    const updateCheckbox = document.getElementById('updateCredentialsCheck');
    const credentialsFields = document.getElementById('credentialsFields');
    const usernameInput = credentialsFields.querySelector('input[name="ELENIA_USERNAME"]');
    
    updateCheckbox.addEventListener('change', () => {
        if (updateCheckbox.checked) {
            credentialsFields.style.display = 'block';
            usernameInput.disabled = false;
        } else {
            credentialsFields.style.display = 'none';
            usernameInput.disabled = true;
        }
    });
});
