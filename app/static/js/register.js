document.addEventListener('DOMContentLoaded', function () {
    const innInput = document.querySelector('input[name="inn"]');
    const findButton = document.createElement('button');
    findButton.type = 'button';
    findButton.className = 'btn btn-outline-primary ms-2';
    findButton.textContent = 'Найти по ИНН';
    findButton.style.whiteSpace = 'nowrap';

    // Wrap INN input in a flex container to append button
    const innGroup = innInput.closest('.form-group');
    if (innGroup) {
        const wrapper = document.createElement('div');
        wrapper.className = 'd-flex align-items-center';
        innInput.parentNode.insertBefore(wrapper, innInput);
        wrapper.appendChild(innInput);
        wrapper.appendChild(findButton);
    }

    findButton.addEventListener('click', function () {
        const inn = innInput.value.trim();
        if (!inn) {
            alert('Пожалуйста, введите ИНН');
            return;
        }

        // Show loading state
        findButton.disabled = true;
        findButton.textContent = 'Поиск...';

        fetch('/api/dadata/company', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
            },
            body: JSON.stringify({ inn: inn })
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    return;
                }

                // Populate fields
                if (data.name) document.querySelector('input[name="company_name"]').value = data.name;
                if (data.address) document.querySelector('input[name="legal_address"]').value = data.address;
                if (data.kpp) {
                    const kppInput = document.querySelector('input[name="kpp"]');
                    if (kppInput) kppInput.value = data.kpp;
                }
                if (data.ogrn) {
                    const ogrnInput = document.querySelector('input[name="ogrn"]');
                    if (ogrnInput) ogrnInput.value = data.ogrn;
                }
                if (data.management_name) {
                    // Try to fill contact person or created separate field if exists
                    // User asked for fields to be read-only, but contact person is usually the registrant.
                    // We'll fill it if empty, but maybe not force read-only for contact person unless specified.
                    // The task said "rest of data ... displayed but not editable".
                    // I will assume company fields are read-only.
                    // data.management_name is usually the CEO.
                    // Let's create a director field or just skip if not in form.
                    // The form has "contact_person".
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Ошибка при поиске организации');
            })
            .finally(() => {
                findButton.disabled = false;
                findButton.textContent = 'Найти по ИНН';
            });
    });
});
