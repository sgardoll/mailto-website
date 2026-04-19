(function() {
    'use strict';

    // -- Helpers --------------------------------------------------------------

    function showError(inputId, message) {
        var span = document.getElementById(inputId + '-error');
        var input = document.getElementById(inputId);
        if (span) {
            span.textContent = message;
            span.hidden = false;
        }
        if (input) {
            input.setAttribute('aria-invalid', 'true');
        }
    }

    function clearError(inputId) {
        var span = document.getElementById(inputId + '-error');
        var input = document.getElementById(inputId);
        if (span) {
            span.textContent = '';
            span.hidden = true;
        }
        if (input) {
            input.setAttribute('aria-invalid', 'false');
        }
    }

    function attachValidation(inputId, rule) {
        var input = document.getElementById(inputId);
        if (!input) return;
        var touched = false;

        function check() {
            var msg = rule(input);
            if (msg) {
                showError(inputId, msg);
            } else {
                clearError(inputId);
            }
        }

        input.addEventListener('blur', function() {
            touched = true;
            check();
        });
        input.addEventListener('input', function() {
            if (touched) check();
        });
    }

    // -- Validation rules -----------------------------------------------------

    function ruleGmailAddress(input) {
        if (!input.value.trim() || input.validity.typeMismatch) {
            return 'Enter a valid Gmail address';
        }
        return '';
    }

    function ruleAppPassword(input) {
        if (input.value.trim().length < 16) {
            return 'Enter your Gmail app password (16 characters)';
        }
        return '';
    }

    function ruleGmailFolder(input) {
        if (!input.value.trim()) {
            return 'Folder name cannot be blank';
        }
        return '';
    }

    function ruleLmsBaseUrl(input) {
        var v = input.value.trim();
        if (!v) return 'Enter a valid URL (e.g. http://localhost:1234/v1)';
        try {
            new URL(v);
            return '';
        } catch (e) {
            return 'Enter a valid URL (e.g. http://localhost:1234/v1)';
        }
    }

    function ruleLmsModel(input) {
        if (!input.value.trim()) return 'Model tag is required';
        return '';
    }

    function ruleLmsTemperature(input) {
        if (input.validity.rangeUnderflow || input.validity.rangeOverflow || input.validity.badInput) {
            return 'Temperature must be between 0.0 and 2.0';
        }
        return '';
    }

    function ruleLmsMaxTokens(input) {
        if (input.validity.rangeUnderflow || input.validity.stepMismatch || input.validity.badInput) {
            return 'Max tokens must be a positive whole number';
        }
        return '';
    }

    function ruleLmsCliPath(input) {
        if (!input.value.trim()) return 'CLI path is required (default: lms)';
        return '';
    }

    // -- Wire validations -----------------------------------------------------

    attachValidation('gmail-address', ruleGmailAddress);
    attachValidation('gmail-app-password', ruleAppPassword);
    attachValidation('gmail-folder', ruleGmailFolder);
    attachValidation('lms-base-url', ruleLmsBaseUrl);
    attachValidation('lms-model', ruleLmsModel);
    attachValidation('lms-temperature', ruleLmsTemperature);
    attachValidation('lms-max-tokens', ruleLmsMaxTokens);
    attachValidation('lms-cli-path', ruleLmsCliPath);

    // -- Show/Hide toggle -----------------------------------------------------

    var toggles = document.querySelectorAll('.toggle-visibility');
    toggles.forEach(function(btn) {
        btn.addEventListener('click', function() {
            var input = document.getElementById(this.dataset.target);
            var isHidden = input.type === 'password';
            input.type = isHidden ? 'text' : 'password';
            this.textContent = isHidden ? 'Hide' : 'Show';
            this.setAttribute('aria-label', (isHidden ? 'Hide ' : 'Show ') + input.labels[0].textContent);
            this.setAttribute('aria-pressed', isHidden ? 'true' : 'false');
        });
    });

    // -- Gmail fan-out display ------------------------------------------------

    var gmailInput = document.getElementById('gmail-address');
    if (gmailInput) {
        gmailInput.addEventListener('input', function() {
            var imapPreview = document.getElementById('imap-user-preview');
            var smtpPreview = document.getElementById('smtp-user-preview');
            if (imapPreview) imapPreview.textContent = this.value;
            if (smtpPreview) smtpPreview.textContent = this.value;
        });
    }

    // -- Allowed senders widget -----------------------------------------------

    var sendersList = document.getElementById('senders-list');
    var addSenderBtn = document.getElementById('add-sender');

    function updateRemoveButtons() {
        var rows = sendersList.querySelectorAll('.sender-row');
        var onlyOne = rows.length === 1;
        rows.forEach(function(row) {
            var btn = row.querySelector('.remove-sender');
            if (btn) btn.disabled = onlyOne;
        });
    }

    function attachSenderValidation(input) {
        var touched = false;
        var errorSpan = null;

        function ensureErrorSpan() {
            if (!errorSpan || !errorSpan.parentNode) {
                errorSpan = input.parentNode.querySelector('.sender-error');
                if (!errorSpan) {
                    errorSpan = document.createElement('span');
                    errorSpan.className = 'sender-error error';
                    errorSpan.hidden = true;
                    errorSpan.setAttribute('aria-live', 'polite');
                    input.parentNode.appendChild(errorSpan);
                }
            }
            return errorSpan;
        }

        function check() {
            var span = ensureErrorSpan();
            var v = input.value.trim();
            if (!v || input.validity.typeMismatch) {
                span.textContent = 'Enter a valid email address';
                span.hidden = false;
                input.setAttribute('aria-invalid', 'true');
            } else {
                span.textContent = '';
                span.hidden = true;
                input.setAttribute('aria-invalid', 'false');
            }
        }

        input.addEventListener('blur', function() {
            touched = true;
            check();
        });
        input.addEventListener('input', function() {
            if (touched) check();
        });
    }

    // Wire validation on initial sender row
    var firstSenderInput = sendersList.querySelector('.sender-input');
    if (firstSenderInput) {
        attachSenderValidation(firstSenderInput);
    }
    updateRemoveButtons();

    if (addSenderBtn) {
        addSenderBtn.addEventListener('click', function() {
            var row = document.createElement('div');
            row.className = 'sender-row';

            var input = document.createElement('input');
            input.type = 'email';
            input.className = 'sender-input';
            input.placeholder = 'sender@example.com';
            input.autocomplete = 'off';

            var removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'remove-sender';
            removeBtn.setAttribute('aria-label', 'Remove sender');
            removeBtn.textContent = 'Remove';

            row.appendChild(input);
            row.appendChild(removeBtn);
            sendersList.appendChild(row);

            attachSenderValidation(input);
            updateRemoveButtons();
            input.focus();
        });
    }

    // Event delegation for remove buttons
    if (sendersList) {
        sendersList.addEventListener('click', function(e) {
            if (e.target.classList.contains('remove-sender') && !e.target.disabled) {
                var row = e.target.closest('.sender-row');
                if (row) {
                    row.remove();
                    updateRemoveButtons();
                }
            }
        });
    }

    // -- Form submit ----------------------------------------------------------

    var form = document.getElementById('wizard-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            var sendersError = document.getElementById('allowed-senders-error');
            var formSummary = document.getElementById('form-error-summary');

            var senders = Array.from(document.querySelectorAll('.sender-input'))
                .map(function(i) { return i.value.trim(); })
                .filter(Boolean);

            if (senders.length === 0) {
                if (sendersError) {
                    sendersError.textContent = 'Add at least one allowed sender';
                    sendersError.hidden = false;
                }
                return;
            }
            if (sendersError) {
                sendersError.textContent = '';
                sendersError.hidden = true;
            }

            var payload = {
                gmail_address: document.getElementById('gmail-address').value.trim(),
                gmail_app_password: document.getElementById('gmail-app-password').value,
                gmail_folder: document.getElementById('gmail-folder').value.trim(),
                allowed_senders: senders,
                lms_base_url: document.getElementById('lms-base-url').value.trim(),
                lms_model: document.getElementById('lms-model').value.trim(),
                lms_temperature: parseFloat(document.getElementById('lms-temperature').value),
                lms_max_tokens: parseInt(document.getElementById('lms-max-tokens').value, 10),
                lms_cli_path: document.getElementById('lms-cli-path').value.trim(),
                autostart: document.getElementById('lms-autostart').checked,
                request_timeout_s: parseInt(document.getElementById('lms-request-timeout').value, 10)
            };

            fetch('/validate-form', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(function(r) { return r.json().then(function(d) { return {status: r.status, data: d}; }); })
            .then(function(result) {
                if (result.data.ok) {
                    if (formSummary) {
                        formSummary.textContent = '';
                        formSummary.hidden = true;
                    }
                } else {
                    if (result.data.errors) {
                        result.data.errors.forEach(function(err) {
                            var fieldId = err.field.replace(/_/g, '-');
                            showError(fieldId, err.message);
                        });
                    }
                    if (formSummary) {
                        formSummary.textContent = 'Fix the highlighted fields before continuing.';
                        formSummary.hidden = false;
                    }
                }
            })
            .catch(function() {
                if (formSummary) {
                    formSummary.textContent = 'Network error. Check your connection and try again.';
                    formSummary.hidden = false;
                }
            });
        });
    }

    // -- Exit button ----------------------------------------------------------

    var exitBtn = document.getElementById('exit-btn');
    if (exitBtn) {
        exitBtn.addEventListener('click', function() {
            exitBtn.disabled = true;
            exitBtn.textContent = 'Exiting...';
            fetch('/exit', {method: 'POST', headers: {'Content-Type': 'application/json'}})
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.ok) {
                        var msg = document.createElement('p');
                        msg.textContent = 'Wizard shut down. You can close this tab.';
                        document.body.textContent = '';
                        document.body.appendChild(msg);
                    }
                })
                .catch(function() {
                    var msg = document.createElement('p');
                    msg.textContent = 'Wizard exiting...';
                    document.body.textContent = '';
                    document.body.appendChild(msg);
                });
        });
    }

})();
