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
        if (!sendersList) return;
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
    var firstSenderInput = sendersList ? sendersList.querySelector('.sender-input') : null;
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

        // Defeat browser/OS password-manager autofill: browsers routinely ignore
        // autocomplete="off" on password inputs. Clear every [data-secret] field
        // after the page settles so any silently filled value from a previous
        // run does not round-trip into config.yaml. Runs twice — once on load
        // and again after a short delay — because some password managers fill
        // asynchronously.
        function clearSecretInputs() {
            document.querySelectorAll('#wizard-form input[data-secret="1"]').forEach(function(el) {
                el.value = '';
            });
        }
        clearSecretInputs();
        setTimeout(clearSecretInputs, 250);

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
        toggleSiteBaseUrl();

        select.addEventListener('change', function() {
            showProvider(this.value);
            toggleSiteBaseUrl();
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

        // SiteGround validations — key is a pasteable textarea
        attachFieldValidation('sg-host', ruleRequired('Host is required'));
        attachFieldValidation('sg-port', rulePort);
        attachFieldValidation('sg-username', ruleRequired('Username is required'));
        function ruleSiteGroundCredential(input) {
            var key = (document.getElementById('sg-ssh_private_key') || {}).value || '';
            var pw = (document.getElementById('sg-password') || {}).value || '';
            var existing = (document.getElementById('sg-existing_key_path') || {}).value || '';
            if (!key.trim() && !pw.trim() && !existing.trim()) {
                return 'Paste an SSH private key or enter a password';
            }
            if (key.trim() && key.indexOf('-----BEGIN') === -1) {
                return 'Paste the full key including -----BEGIN ... -----END lines';
            }
            return '';
        }
        attachFieldValidation('sg-ssh_private_key', ruleSiteGroundCredential);
        attachFieldValidation('sg-remote_base_path', ruleRequired('Remote base path is required'));
        // Also recheck the credential error when password changes
        var sgPassword = document.getElementById('sg-password');
        if (sgPassword) {
            sgPassword.addEventListener('blur', function() {
                var keyInput = document.getElementById('sg-ssh_private_key');
                if (keyInput) {
                    var msg = ruleSiteGroundCredential(keyInput);
                    if (msg) { showFieldError('sg-ssh_private_key', msg); } else { clearFieldError('sg-ssh_private_key'); }
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

        // Vercel validations
        attachFieldValidation('vercel-api-token', ruleRequired('API token is required'));
        attachFieldValidation('vercel-project-id', ruleRequired('Project name or ID is required'));

        // Site base URL validation (only when manual — SSH providers)
        attachFieldValidation('site-base-url', function(input) {
            if (!siteBaseUrlIsManual(select.value)) return '';
            var v = input.value.trim();
            if (!v) return 'Site base URL is required';
            if (!/^https?:\/\//i.test(v)) return 'Enter a valid URL (e.g. https://example.com)';
            return '';
        });

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

                if (prefix === 'sg-') {
                    var key = (document.getElementById('sg-ssh_private_key') || {}).value || '';
                    var pw = (document.getElementById('sg-password') || {}).value || '';
                    var existing = (document.getElementById('sg-existing_key_path') || {}).value || '';
                    if (!key.trim() && !pw.trim() && !existing.trim()) {
                        showFieldError('sg-ssh_private_key', 'Paste an SSH private key or enter a password');
                        errors.push(1);
                    } else if (key.trim() && key.indexOf('-----BEGIN') === -1) {
                        showFieldError('sg-ssh_private_key', 'Paste the full key including -----BEGIN ... -----END lines');
                        errors.push(1);
                    } else { clearFieldError('sg-ssh_private_key'); }
                } else {
                    var kp = document.getElementById(prefix + 'ssh_key_path').value.trim();
                    var pw = document.getElementById(prefix + 'password').value.trim();
                    if (!kp && !pw) {
                        showFieldError(prefix + 'ssh_key_path', 'Enter an SSH key path or a password — at least one is required');
                        errors.push(1);
                    } else { clearFieldError(prefix + 'ssh_key_path'); }
                }

                if (!document.getElementById(prefix + 'remote_base_path').value.trim()) {
                    showFieldError(prefix + 'remote_base_path', 'Remote base path is required'); errors.push(1);
                } else { clearFieldError(prefix + 'remote_base_path'); }

            } else if (provider === 'vercel') {
                if (!document.getElementById('vercel-api-token').value.trim()) {
                    showFieldError('vercel-api-token', 'API token is required'); errors.push(1);
                } else { clearFieldError('vercel-api-token'); }
                if (!document.getElementById('vercel-project-id').value.trim()) {
                    showFieldError('vercel-project-id', 'Project name or ID is required'); errors.push(1);
                } else { clearFieldError('vercel-project-id'); }
            }

            if (siteBaseUrlIsManual(provider)) {
                var baseInput = document.getElementById('site-base-url');
                var baseVal = baseInput ? baseInput.value.trim() : '';
                if (!baseVal) {
                    showFieldError('site-base-url', 'Site base URL is required'); errors.push(1);
                } else if (!/^https?:\/\//i.test(baseVal)) {
                    showFieldError('site-base-url', 'Enter a valid URL (e.g. https://example.com)'); errors.push(1);
                } else { clearFieldError('site-base-url'); }
            } else {
                clearFieldError('site-base-url');
            }

            return errors.length === 0;
        }

        function siteBaseUrlIsManual(provider) {
            return provider === 'siteground' || provider === 'ssh_sftp';
        }

        function toggleSiteBaseUrl() {
            var group = document.getElementById('site-base-url-group');
            if (!group) return;
            var show = siteBaseUrlIsManual(select.value);
            group.hidden = !show;
            group.setAttribute('aria-hidden', show ? 'false' : 'true');
        }

        function buildHostingPayload() {
            var provider = select.value;
            var prefix = provider === 'siteground' ? 'sg-' : (provider === 'ssh_sftp' ? 'ssh-' : null);
            var payload = { step: 'hosting', hosting_provider: provider };

            if (prefix) {
                payload[prefix + 'host'] = document.getElementById(prefix + 'host').value.trim();
                payload[prefix + 'port'] = document.getElementById(prefix + 'port').value.trim();
                payload[prefix + 'username'] = document.getElementById(prefix + 'username').value.trim();
                if (prefix === 'sg-') {
                    // SiteGround: pasteable private key textarea + hidden existing-key path from hydration
                    payload['sg-ssh_private_key'] = (document.getElementById('sg-ssh_private_key') || {}).value || '';
                    var sgExisting = document.getElementById('sg-existing_key_path');
                    if (sgExisting) payload['sg-existing_key_path'] = sgExisting.value || '';
                    payload['sg-key_passphrase'] = (document.getElementById('sg-key_passphrase') || {}).value || '';
                } else {
                    payload[prefix + 'ssh_key_path'] = document.getElementById(prefix + 'ssh_key_path').value.trim();
                }
                payload[prefix + 'password'] = document.getElementById(prefix + 'password').value;
                payload[prefix + 'remote_base_path'] = document.getElementById(prefix + 'remote_base_path').value.trim();
            } else if (provider === 'vercel') {
                payload['vercel_api_token'] = document.getElementById('vercel-api-token').value.trim();
                payload['vercel_project_id'] = document.getElementById('vercel-project-id').value.trim();
            }

            if (siteBaseUrlIsManual(provider)) {
                var base = document.getElementById('site-base-url');
                if (base) payload['site_base_url'] = base.value.trim();
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

        function validateSiteNameInput(input) {
            var span = input.closest('.field-group').querySelector('.error');
            if (!input.value.trim()) {
                showErrSpan(span, input, 'Site name is required');
                return false;
            }
            clearErrSpan(span, input);
            return true;
        }

        // -- Attach validation to a row's inputs ----------------------------

        function attachRowValidation(row) {
            var slugInput = row.querySelector('.inbox-slug');
            var siteNameInput = row.querySelector('.inbox-site-name');

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
            if (siteNameInput) makeTouched(siteNameInput, validateSiteNameInput);
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
                {cls: 'inbox-site-name', base: 'inbox-site-name-' + n},
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
                var n = validateSiteNameInput(row.querySelector('.inbox-site-name'));
                if (!s || !n) ok = false;
            });
            validateAllSlugs();
            if (inboxesList.querySelectorAll('.inbox-slug[aria-invalid="true"]').length > 0) ok = false;
            return ok;
        }

        function buildInboxesPayload() {
            var inboxes = [];
            inboxesList.querySelectorAll('.inbox-row').forEach(function(row) {
                inboxes.push({
                    slug: row.querySelector('.inbox-slug').value.trim(),
                    site_name: row.querySelector('.inbox-site-name').value.trim(),
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
                                            inbox_site_name: '.inbox-site-name',
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


// ── Phase 4: Preview step ────────────────────────────────────────────────────

(function() {
    'use strict';

    function initPreviewStep() {
        var writeBtn = document.getElementById('write-btn');
        if (!writeBtn) return;  // Not on the preview page

        var overwriteCheckbox = document.getElementById('overwrite-confirm');
        var writeError = document.getElementById('write-error');
        var hasExisting = writeBtn.dataset.hasExisting === 'true';

        // If existing config detected, keep the button disabled until checkbox is checked.
        if (hasExisting && overwriteCheckbox) {
            writeBtn.disabled = true;
            overwriteCheckbox.addEventListener('change', function() {
                writeBtn.disabled = !this.checked;
            });
        }

        writeBtn.addEventListener('click', function() {
            writeBtn.disabled = true;
            if (writeError) { writeError.textContent = ''; writeError.hidden = true; }

            var payload = { confirmed: true };
            if (hasExisting && overwriteCheckbox) {
                payload.overwrite_confirmed = overwriteCheckbox.checked;
            }

            fetch('/write-config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            })
            .then(function(r) { return r.json().then(function(d) { return {status: r.status, data: d}; }); })
            .then(function(result) {
                if (result.data.ok) {
                    window.location.href = result.data.next_step || '/step/done';
                } else {
                    var msg = result.data.error || 'Write failed. Please try again.';
                    if (writeError) { writeError.textContent = msg; writeError.hidden = false; }
                    // Re-enable the button (respecting the overwrite gate)
                    if (!hasExisting || (overwriteCheckbox && overwriteCheckbox.checked)) {
                        writeBtn.disabled = false;
                    }
                }
            })
            .catch(function() {
                if (writeError) {
                    writeError.textContent = 'Network error. Check your connection and try again.';
                    writeError.hidden = false;
                }
                if (!hasExisting || (overwriteCheckbox && overwriteCheckbox.checked)) {
                    writeBtn.disabled = false;
                }
            });
        });

        // Exit button (preview page has its own footer exit button)
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

    initPreviewStep();

    // ──────────────────────────────────────────────────────────
    //  Done step — deploy launcher (SiteGround only)
    // ──────────────────────────────────────────────────────────
    function initDoneStep() {
        var deployBtn = document.getElementById('deploy-btn');
        if (!deployBtn) return;

        var launchPanel = document.getElementById('deploy-launch');
        var panel = document.getElementById('deploy-panel');
        var label = document.getElementById('deploy-status-label');
        var errorEl = document.getElementById('deploy-error');

        function updateRow(row) {
            var li = document.querySelector('#deploy-inboxes li[data-slug="' + CSS.escape(row.slug) + '"]');
            if (!li) return;
            var badge = li.querySelector('.deploy-phase-badge');
            var detail = li.querySelector('.deploy-row-detail');
            var link = li.querySelector('.deploy-row-link');
            if (badge) {
                badge.textContent = row.phase || 'pending';
                badge.setAttribute('data-phase', row.phase || 'pending');
            }
            if (detail) detail.textContent = row.detail || '';
            li.classList.toggle('ok', !!row.ok);
            li.classList.toggle('failed', !!row.error);
            if (link && row.ok && row.url) {
                link.hidden = false;
                link.href = row.url;
                link.textContent = row.url;
            }
        }

        function pollStatus() {
            fetch('/deploy-status')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (label) label.textContent = data.status || 'unknown';
                    (data.inboxes || []).forEach(updateRow);
                    if (data.error && errorEl) {
                        errorEl.textContent = data.error;
                        errorEl.hidden = false;
                    }
                    if (data.status === 'running') {
                        setTimeout(pollStatus, 2000);
                    } else if (data.status === 'failed' && errorEl && !data.error) {
                        errorEl.textContent = 'One or more inboxes failed to deploy. See per-inbox errors above.';
                        errorEl.hidden = false;
                    }
                })
                .catch(function() { setTimeout(pollStatus, 5000); });
        }

        deployBtn.addEventListener('click', function() {
            deployBtn.disabled = true;
            deployBtn.textContent = 'Deploying…';
            if (errorEl) { errorEl.textContent = ''; errorEl.hidden = true; }

            fetch('/deploy', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(function(r) { return r.json().then(function(d) { return {status: r.status, data: d}; }); })
            .then(function(result) {
                if (result.data.ok) {
                    if (launchPanel) launchPanel.hidden = true;
                    if (panel) panel.hidden = false;
                    pollStatus();
                } else {
                    deployBtn.disabled = false;
                    deployBtn.textContent = 'Deploy';
                    var msg = result.data.message || result.data.error || 'Deploy failed to start.';
                    if (errorEl) { errorEl.textContent = msg; errorEl.hidden = false; }
                    else { alert(msg); }
                }
            })
            .catch(function() {
                deployBtn.disabled = false;
                deployBtn.textContent = 'Deploy';
                if (errorEl) {
                    errorEl.textContent = 'Network error. Check the wizard server and try again.';
                    errorEl.hidden = false;
                }
            });
        });
    }

    initDoneStep();

})();
