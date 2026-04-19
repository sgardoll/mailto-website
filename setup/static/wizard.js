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
    var isGmailStep = !!document.getElementById('gmail-address');
    var isLmStudioStep = !isGmailStep && !!document.getElementById('lms-base-url');

    if (form && (isGmailStep || isLmStudioStep)) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            var sendersError = document.getElementById('allowed-senders-error');
            var formSummary = document.getElementById('form-error-summary');
            var payload;

            if (isGmailStep) {
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

                payload = {
                    step: 'gmail',
                    gmail_address: document.getElementById('gmail-address').value.trim(),
                    gmail_app_password: document.getElementById('gmail-app-password').value,
                    gmail_folder: document.getElementById('gmail-folder').value.trim(),
                    allowed_senders: senders
                };
            } else {
                payload = {
                    step: 'lmstudio',
                    lms_base_url: document.getElementById('lms-base-url').value.trim(),
                    lms_model: document.getElementById('lms-model').value.trim(),
                    lms_temperature: parseFloat(document.getElementById('lms-temperature').value),
                    lms_max_tokens: parseInt(document.getElementById('lms-max-tokens').value, 10),
                    lms_cli_path: document.getElementById('lms-cli-path').value.trim(),
                    autostart: document.getElementById('lms-autostart').checked,
                    request_timeout_s: parseInt(document.getElementById('lms-request-timeout').value, 10)
                };
            }

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
                    if (result.data.next_step) {
                        window.location.href = result.data.next_step;
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


// ── Phase 3: Inboxes step ────────────────────────────────────────────────────

(function() {
    'use strict';

    // -- Helpers (scoped to inboxes IIFE) ------------------------------------

    function showErrSpan(span, input, message) {
        if (span) { span.textContent = message; span.hidden = false; }
        if (input) { input.setAttribute('aria-invalid', 'true'); }
    }

    function clearErrSpan(span, input) {
        if (span) { span.textContent = ''; span.hidden = true; }
        if (input) { input.setAttribute('aria-invalid', 'false'); }
    }

    // -- Inboxes step --------------------------------------------------------

    function initInboxesStep() {
        var inboxesList = document.getElementById('inboxes-list');
        var addInboxBtn = document.getElementById('add-inbox');
        if (!inboxesList && !addInboxBtn) return;

        var inboxCounter = 1; // First row already rendered with index 1

        function updateRemoveButtons() {
            var rows = inboxesList.querySelectorAll('.inbox-row');
            var removeButtons = inboxesList.querySelectorAll('.remove-inbox');
            var onlyOne = rows.length === 1;
            removeButtons.forEach(function(btn, i) {
                btn.disabled = onlyOne;
            });
        }

        // -- Slug uniqueness -------------------------------------------------

        function validateAllSlugs() {
            var slugInputs = Array.from(inboxesList.querySelectorAll('.inbox-slug'));
            var values = slugInputs.map(function(i) { return i.value.trim().toLowerCase(); });
            var counts = {};
            values.forEach(function(v) { counts[v] = (counts[v] || 0) + 1; });

            slugInputs.forEach(function(input) {
                var span = input.closest('.field-group').querySelector('.error');
                var val = input.value.trim().toLowerCase();
                // Only override with uniqueness error if field has no other active error
                var currentErr = span ? span.textContent : '';
                var isDupErr = currentErr === 'Slug must be unique across all inboxes';
                if (counts[val] > 1 && val !== '') {
                    showErrSpan(span, input, 'Slug must be unique across all inboxes');
                } else if (isDupErr) {
                    clearErrSpan(span, input);
                }
            });
        }

        // -- Per-field validation rules --------------------------------------

        var SLUG_RE = /^[a-z0-9-]+$/;

        function validateSlugInput(input) {
            var span = input.closest('.field-group').querySelector('.error');
            var val = input.value.trim();
            if (!val) {
                showErrSpan(span, input, 'Slug is required');
                return false;
            }
            if (!SLUG_RE.test(val)) {
                showErrSpan(span, input, 'Slug may only contain lowercase letters, numbers, and hyphens');
                return false;
            }
            clearErrSpan(span, input);
            return true;
        }

        function validateEmailInput(input) {
            var span = input.closest('.field-group').querySelector('.error');
            var val = input.value.trim();
            if (!val || input.validity.typeMismatch || !val.includes('@')) {
                showErrSpan(span, input, 'Enter a valid email address');
                return false;
            }
            clearErrSpan(span, input);
            return true;
        }

        function validateSiteNameInput(input) {
            var span = input.closest('.field-group').querySelector('.error');
            if (!input.value.trim()) {
                showErrSpan(span, input, 'Site name is required');
                return false;
            }
            clearErrSpan(span, input);
            return true;
        }

        function validateSiteUrlInput(input) {
            var span = input.closest('.field-group').querySelector('.error');
            var val = input.value.trim();
            var valid = false;
            try { new URL(val); valid = true; } catch(e) {}
            if (!valid) {
                showErrSpan(span, input, 'Enter a valid URL (e.g. https://example.com)');
                return false;
            }
            clearErrSpan(span, input);
            return true;
        }

        function validateBasePathInput(input) {
            var span = input.closest('.field-group').querySelector('.error');
            var val = input.value.trim();
            if (!val || val[0] !== '/') {
                showErrSpan(span, input, 'Base path must start with /');
                return false;
            }
            clearErrSpan(span, input);
            return true;
        }

        // -- Attach validation to a row's inputs ----------------------------

        function attachRowValidation(row) {
            var slugInput = row.querySelector('.inbox-slug');
            var emailInput = row.querySelector('.inbox-email');
            var siteNameInput = row.querySelector('.inbox-site-name');
            var siteUrlInput = row.querySelector('.inbox-site-url');
            var basePathInput = row.querySelector('.inbox-base-path');

            function makeTouched(input, validator) {
                var touched = false;
                input.addEventListener('blur', function() {
                    touched = true;
                    validator(input);
                    if (input.classList.contains('inbox-slug')) validateAllSlugs();
                });
                input.addEventListener('input', function() {
                    if (touched) {
                        validator(input);
                        if (input.classList.contains('inbox-slug')) validateAllSlugs();
                    }
                });
            }

            if (slugInput) makeTouched(slugInput, validateSlugInput);
            if (emailInput) makeTouched(emailInput, validateEmailInput);
            if (siteNameInput) makeTouched(siteNameInput, validateSiteNameInput);
            if (siteUrlInput) makeTouched(siteUrlInput, validateSiteUrlInput);
            if (basePathInput) makeTouched(basePathInput, validateBasePathInput);
        }

        // -- Clone and add new row ------------------------------------------

        function addInboxRow() {
            var tmpl = document.getElementById('inbox-row-template');
            if (!tmpl) return;
            inboxCounter++;
            var n = inboxCounter;
            var clone = tmpl.content.cloneNode(true);
            var row = clone.querySelector('.inbox-row');

            // Update label
            var label = row.querySelector('.inbox-row-label');
            if (label) label.textContent = 'Inbox ' + n;

            // Update remove button aria-label
            var removeBtn = row.querySelector('.remove-inbox');
            if (removeBtn) removeBtn.setAttribute('aria-label', 'Remove inbox ' + n);

            // Assign IDs and aria-describedby to each input
            var fields = [
                {cls: 'inbox-slug', base: 'inbox-slug-' + n},
                {cls: 'inbox-email', base: 'inbox-email-' + n},
                {cls: 'inbox-site-name', base: 'inbox-site-name-' + n},
                {cls: 'inbox-site-url', base: 'inbox-site-url-' + n},
                {cls: 'inbox-base-path', base: 'inbox-base-path-' + n},
            ];
            fields.forEach(function(f) {
                var input = row.querySelector('.' + f.cls);
                var span = input ? input.closest('.field-group').querySelector('.error') : null;
                var helpSpan = input ? input.closest('.field-group').querySelector('.help-text') : null;
                if (input) {
                    input.id = f.base;
                    var describedby = '';
                    if (helpSpan) { helpSpan.id = f.base + '-help'; describedby += f.base + '-help '; }
                    if (span) { span.id = f.base + '-error'; describedby += f.base + '-error'; }
                    input.setAttribute('aria-describedby', describedby.trim());
                }
                // Update label for= if label exists
                var lbl = input ? input.closest('.field-group').querySelector('label') : null;
                if (lbl) lbl.setAttribute('for', f.base);
            });

            inboxesList.appendChild(row);
            attachRowValidation(inboxesList.lastElementChild);
            updateRemoveButtons();
            var firstInput = inboxesList.lastElementChild.querySelector('.inbox-slug');
            if (firstInput) firstInput.focus();
        }

        // Init: attach validation to pre-rendered first row
        var firstRow = inboxesList.querySelector('.inbox-row');
        if (firstRow) attachRowValidation(firstRow);
        updateRemoveButtons();

        // Add inbox button
        if (addInboxBtn) {
            addInboxBtn.addEventListener('click', addInboxRow);
        }

        // Remove delegation
        inboxesList.addEventListener('click', function(e) {
            if (e.target.classList.contains('remove-inbox') && !e.target.disabled) {
                var row = e.target.closest('.inbox-row');
                if (row) {
                    row.remove();
                    updateRemoveButtons();
                    validateAllSlugs();
                }
            }
        });

        // -- Form submit --------------------------------------------------

        function validateAllRows() {
            var ok = true;
            inboxesList.querySelectorAll('.inbox-row').forEach(function(row) {
                var s = validateSlugInput(row.querySelector('.inbox-slug'));
                var e = validateEmailInput(row.querySelector('.inbox-email'));
                var n = validateSiteNameInput(row.querySelector('.inbox-site-name'));
                var u = validateSiteUrlInput(row.querySelector('.inbox-site-url'));
                var b = validateBasePathInput(row.querySelector('.inbox-base-path'));
                if (!s || !e || !n || !u || !b) ok = false;
            });
            validateAllSlugs();
            // Check if any slug still has error after uniqueness check
            if (inboxesList.querySelectorAll('.inbox-slug[aria-invalid="true"]').length > 0) ok = false;
            return ok;
        }

        function buildInboxesPayload() {
            var inboxes = [];
            inboxesList.querySelectorAll('.inbox-row').forEach(function(row) {
                inboxes.push({
                    slug: row.querySelector('.inbox-slug').value.trim(),
                    email: row.querySelector('.inbox-email').value.trim(),
                    site_name: row.querySelector('.inbox-site-name').value.trim(),
                    site_url: row.querySelector('.inbox-site-url').value.trim(),
                    base_path: row.querySelector('.inbox-base-path').value.trim(),
                });
            });
            return {step: 'inboxes', inboxes: inboxes};
        }

        var form = document.getElementById('wizard-form');
        if (form) {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                var formSummary = document.getElementById('form-error-summary');
                if (!validateAllRows()) {
                    if (formSummary) { formSummary.textContent = 'Fix the highlighted fields before continuing.'; formSummary.hidden = false; }
                    return;
                }
                if (formSummary) { formSummary.textContent = ''; formSummary.hidden = true; }

                var payload = buildInboxesPayload();
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
                            // Map server errors to row fields by index
                            result.data.errors.forEach(function(err) {
                                if (typeof err.index === 'number') {
                                    var rows = inboxesList.querySelectorAll('.inbox-row');
                                    var row = rows[err.index];
                                    if (row) {
                                        var clsMap = {
                                            inbox_slug: '.inbox-slug',
                                            inbox_email: '.inbox-email',
                                            inbox_site_name: '.inbox-site-name',
                                            inbox_site_url: '.inbox-site-url',
                                            inbox_base_path: '.inbox-base-path',
                                        };
                                        var cls = clsMap[err.field];
                                        if (cls) {
                                            var input = row.querySelector(cls);
                                            var span = input ? input.closest('.field-group').querySelector('.error') : null;
                                            if (input) showErrSpan(span, input, err.message);
                                        }
                                    }
                                }
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

    initInboxesStep();

})();
