document.addEventListener('DOMContentLoaded', function () {
    const contactLink = document.querySelector('a[href="#contact"]'); // Or by ID if we set one
    const footerContactLink = Array.from(document.querySelectorAll('.footer-link')).find(el => el.textContent.trim() === 'Контакты');
    const modal = document.getElementById('contact-modal');
    const closeBtn = document.querySelector('.contact-modal-close');
    const form = document.getElementById('contact-form');

    // Attach event to footer link
    if (footerContactLink) {
        footerContactLink.addEventListener('click', function (e) {
            e.preventDefault();
            openModal();
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    // Close on click outside
    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === modal) {
                closeModal();
            }
        });
    }

    // Handle Form Submission
    if (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();

            const submitBtn = form.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Отправка...';

            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            fetch('/contact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
                },
                body: JSON.stringify(data)
            })
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        showStatus('success', 'Ваше сообщение успешно отправлено!');
                        form.reset();
                        setTimeout(closeModal, 2000);
                    } else {
                        showStatus('error', result.message || 'Произошла ошибка. Попробуйте позже.');
                    }
                })
                .catch(error => {
                    showStatus('error', 'Ошибка сети. Проверьте соединение.');
                    console.error('Error:', error);
                })
                .finally(() => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                });
        });
    }

    function openModal() {
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    function closeModal() {
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
            hideStatus();
        }
    }

    function showStatus(type, message) {
        const statusDiv = document.getElementById('contact-form-status');
        if (statusDiv) {
            statusDiv.className = `alert alert-${type === 'success' ? 'success' : 'danger'} mt-3`;
            statusDiv.textContent = message;
            statusDiv.style.display = 'block';
        }
    }

    function hideStatus() {
        const statusDiv = document.getElementById('contact-form-status');
        if (statusDiv) {
            statusDiv.style.display = 'none';
        }
    }
});
