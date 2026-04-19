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


// ── Phase 3: Hosting step ────────────────────────────────────────────────────

(function() {
    'use strict';

    // -- Shared helpers (scoped to Phase 3 IIFE) ----------------------------

    function showFieldError(fieldId, message) {
        var span = document.getElementById(fieldId + '-error');
        var input = document.getElementById(fieldId);
        if (span) { span.textContent = message; span.hidden = false; }
        if (input) { input.setAttribute('aria-invalid', 'true'); }
    }

    function clearFieldError(fieldId) {
        var span = document.getElementById(fieldId + '-error');
        var input = document.getElementById(fieldId);
        if (span) { span.textContent = ''; span.hidden = true; }
        if (input) { input.setAttribute('aria-invalid', 'false'); }
    }

    function attachFieldValidation(fieldId, rule) {
        var input = document.getElementById(fieldId);
        if (!input) return;
        var touched = false;
        function check() {
            var msg = rule(input);
            if (msg) { showFieldError(fieldId, msg); } else { clearFieldError(fieldId); }
        }
        input.addEventListener('blur', function() { touched = true; check(); });
        input.addEventListener('input', function() { if (touched) check(); });
    }

    // -- Hosting step --------------------------------------------------------

    function initHostingStep() {
        var select = document.getElementById('hosting-provider');
        if (!select) return;

        // Wire show/hide toggles for password fields in hosting step
        document.querySelectorAll('#wizard-form .toggle-visibility').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var input = document.getElementById(this.dataset.target);
                if (!input) return;
                var isHidden = input.type === 'password';
                input.type = isHidden ? 'text' : 'password';
                this.textContent = isHidden ? 'Hide' : 'Show';
                this.setAttribute('aria-pressed', isHidden ? 'true' : 'false');
            });
        });

        // Provider show/hide
        function showProvider(val) {
            document.querySelectorAll('.provider-fields').forEach(function(g) {
                var show = g.dataset.provider === val;
                g.hidden = !show;
                g.setAttribute('aria-hidden', show ? 'false' : 'true');
            });
        }

        showProvider(select.value);

        select.addEventListener('change', function() {
            showProvider(this.value);
        });

        // Validation rules
        function ruleRequired(msg) {
            return function(input) { return input.value.trim() ? '' : msg; };
        }
        function rulePort(input) {
            var v = parseInt(input.value, 10);
            if (isNaN(v) || v < 1 || v > 65535) return 'Port must be a number between 1 and 65535';
            return '';
        }
        function ruleAtLeastOne(keyPathId, passwordId) {
            return function(input) {
                var keyPath = document.getElementById(keyPathId);
                var password = document.getElementById(passwordId);
                if ((!keyPath || !keyPath.value.trim()) && (!password || !password.value.trim())) {
                    return 'Enter an SSH key path or a password — at least one is required';
                }
                return '';
            };
        }

        // SiteGround validations
        attachFieldValidation('sg-host', ruleRequired('Host is required'));
        attachFieldValidation('sg-port', rulePort);
        attachFieldValidation('sg-username', ruleRequired('Username is required'));
        attachFieldValidation('sg-ssh_key_path', ruleAtLeastOne('sg-ssh_key_path', 'sg-password'));
        attachFieldValidation('sg-remote_base_path', ruleRequired('Remote base path is required'));
        // Also recheck key_path error when password changes
        var sgPassword = document.getElementById('sg-password');
        if (sgPassword) {
            sgPassword.addEventListener('blur', function() {
                var keyPathInput = document.getElementById('sg-ssh_key_path');
                if (keyPathInput) {
                    var msg = ruleAtLeastOne('sg-ssh_key_path', 'sg-password')(keyPathInput);
                    if (msg) { showFieldError('sg-ssh_key_path', msg); } else { clearFieldError('sg-ssh_key_path'); }
                }
            });
        }

        // SSH/SFTP validations
        attachFieldValidation('ssh-host', ruleRequired('Host is required'));
        attachFieldValidation('ssh-port', rulePort);
        attachFieldValidation('ssh-username', ruleRequired('Username is required'));
        attachFieldValidation('ssh-ssh_key_path', ruleAtLeastOne('ssh-ssh_key_path', 'ssh-password'));
        attachFieldValidation('ssh-remote_base_path', ruleRequired('Remote base path is required'));
        var sshPassword = document.getElementById('ssh-password');
        if (sshPassword) {
            sshPassword.addEventListener('blur', function() {
                var keyPathInput = document.getElementById('ssh-ssh_key_path');
                if (keyPathInput) {
                    var msg = ruleAtLeastOne('ssh-ssh_key_path', 'ssh-password')(keyPathInput);
                    if (msg) { showFieldError('ssh-ssh_key_path', msg); } else { clearFieldError('ssh-ssh_key_path'); }
                }
            });
        }

        // Netlify validations
        attachFieldValidation('netlify-api-token', ruleRequired('API token is required'));
        attachFieldValidation('netlify-site-id', ruleRequired('Site ID is required'));

        // Vercel validations
        attachFieldValidation('vercel-api-token', ruleRequired('API token is required'));
        attachFieldValidation('vercel-project-id', ruleRequired('Project name or ID is required'));

        // GitHub Pages validations
        attachFieldValidation('gh-pages-branch', ruleRequired('Target branch is required'));

        // -- Form submit ---------------------------------------------------------
        function validateVisibleProvider() {
            var provider = select.value;
            var errors = [];
            var prefix = provider === 'siteground' ? 'sg-' : (provider === 'ssh_sftp' ? 'ssh-' : null);

            if (prefix) {
                if (!document.getElementById(prefix + 'host').value.trim()) {
                    showFieldError(prefix + 'host', 'Host is required'); errors.push(1);
                } else { clearFieldError(prefix + 'host'); }

                var port = parseInt(document.getElementById(prefix + 'port').value, 10);
                if (isNaN(port) || port < 1 || port > 65535) {
                    showFieldError(prefix + 'port', 'Port must be a number between 1 and 65535'); errors.push(1);
                } else { clearFieldError(prefix + 'port'); }

                if (!document.getElementById(prefix + 'username').value.trim()) {
                    showFieldError(prefix + 'username', 'Username is required'); errors.push(1);
                } else { clearFieldError(prefix + 'username'); }

                var kp = document.getElementById(prefix + 'ssh_key_path').value.trim();
                var pw = document.getElementById(prefix + 'password').value.trim();
                if (!kp && !pw) {
                    showFieldError(prefix + 'ssh_key_path', 'Enter an SSH key path or a password — at least one is required');
                    errors.push(1);
                } else { clearFieldError(prefix + 'ssh_key_path'); }

                if (!document.getElementById(prefix + 'remote_base_path').value.trim()) {
                    showFieldError(prefix + 'remote_base_path', 'Remote base path is required'); errors.push(1);
                } else { clearFieldError(prefix + 'remote_base_path'); }

            } else if (provider === 'netlify') {
                if (!document.getElementById('netlify-api-token').value.trim()) {
                    showFieldError('netlify-api-token', 'API token is required'); errors.push(1);
                } else { clearFieldError('netlify-api-token'); }
                if (!document.getElementById('netlify-site-id').value.trim()) {
                    showFieldError('netlify-site-id', 'Site ID is required'); errors.push(1);
                } else { clearFieldError('netlify-site-id'); }

            } else if (provider === 'vercel') {
                if (!document.getElementById('vercel-api-token').value.trim()) {
                    showFieldError('vercel-api-token', 'API token is required'); errors.push(1);
                } else { clearFieldError('vercel-api-token'); }
                if (!document.getElementById('vercel-project-id').value.trim()) {
                    showFieldError('vercel-project-id', 'Project name or ID is required'); errors.push(1);
                } else { clearFieldError('vercel-project-id'); }

            } else if (provider === 'github_pages') {
                if (!document.getElementById('gh-pages-branch').value.trim()) {
                    showFieldError('gh-pages-branch', 'Target branch is required'); errors.push(1);
                } else { clearFieldError('gh-pages-branch'); }
            }

            return errors.length === 0;
        }

        function buildHostingPayload() {
            var provider = select.value;
            var prefix = provider === 'siteground' ? 'sg-' : (provider === 'ssh_sftp' ? 'ssh-' : null);
            var payload = { step: 'hosting', hosting_provider: provider };

            if (prefix) {
                payload[prefix + 'host'] = document.getElementById(prefix + 'host').value.trim();
                payload[prefix + 'port'] = document.getElementById(prefix + 'port').value.trim();
                payload[prefix + 'username'] = document.getElementById(prefix + 'username').value.trim();
                payload[prefix + 'ssh_key_path'] = document.getElementById(prefix + 'ssh_key_path').value.trim();
                payload[prefix + 'password'] = document.getElementById(prefix + 'password').value;
                payload[prefix + 'remote_base_path'] = document.getElementById(prefix + 'remote_base_path').value.trim();
            } else if (provider === 'netlify') {
                payload['netlify_api_token'] = document.getElementById('netlify-api-token').value.trim();
                payload['netlify_site_id'] = document.getElementById('netlify-site-id').value.trim();
            } else if (provider === 'vercel') {
                payload['vercel_api_token'] = document.getElementById('vercel-api-token').value.trim();
                payload['vercel_project_id'] = document.getElementById('vercel-project-id').value.trim();
            } else if (provider === 'github_pages') {
                payload['gh_pages_branch'] = document.getElementById('gh-pages-branch').value.trim();
            }

            return payload;
        }

        var form = document.getElementById('wizard-form');
        if (form) {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                var formSummary = document.getElementById('form-error-summary');
                if (!validateVisibleProvider()) {
                    if (formSummary) { formSummary.textContent = 'Fix the highlighted fields before continuing.'; formSummary.hidden = false; }
                    return;
                }
                if (formSummary) { formSummary.textContent = ''; formSummary.hidden = true; }

                var payload = buildHostingPayload();
                fetch('/validate-form', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                })
                .then(function(r) { return r.json().then(function(d) { return {status: r.status, data: d}; }); })
                .then(function(result) {
                    if (result.data.ok) {
                        window.location.href = result.data.next_step;
                    } else {
                        if (result.data.errors) {
                            result.data.errors.forEach(function(err) {
                                showFieldError(err.field, err.message);
                            });
                        }
                        if (formSummary) { formSummary.textContent = 'Fix the highlighted fields before continuing.'; formSummary.hidden = false; }
                    }
                })
                .catch(function() {
                    if (formSummary) { formSummary.textContent = 'Network error. Check your connection and try again.'; formSummary.hidden = false; }
                });
            });
        }

        // Exit button
        var exitBtn = document.getElementById('exit-btn');
        if (exitBtn) {
            exitBtn.addEventListener('click', function() {
                exitBtn.disabled = true;
                exitBtn.textContent = 'Exiting...';
                fetch('/exit', {method: 'POST', headers: {'Content-Type': 'application/json'}})
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        if (data.ok) { document.body.textContent = ''; var msg = document.createElement('p'); msg.textContent = 'Wizard shut down. You can close this tab.'; document.body.appendChild(msg); }
                    })
                    .catch(function() { document.body.textContent = ''; var msg = document.createElement('p'); msg.textContent = 'Wizard exiting...'; document.body.appendChild(msg); });
            });
        }
    }

    initHostingStep();

})();
