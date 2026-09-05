// Identity Signal frontend — preserves the existing Flask/SSE API contract.

document.addEventListener('DOMContentLoaded', () => {
    const $ = (id) => document.getElementById(id);
    const uploadArea = $('upload-area');
    const fileInput = $('file-input');
    const uploadPreview = $('upload-preview');
    const previewImage = $('preview-image');
    const changeImageBtn = $('change-image');
    const analyzeBtn = $('analyze-btn');
    const progressSection = $('progress-section');
    const resultsSection = $('results-section');
    const errorSection = $('error-section');
    const errorMessage = $('error-message');
    const retryBtn = $('retry-btn');
    const logOutput = $('log-output');
    const consoleStatus = $('console-status');
    const consoleDetail = $('console-detail');
    const resultStamp = $('result-stamp');
    const scannerProgress = $('scanner-progress');
    const scannerFill = $('scanner-meter-fill');
    const trackFill = $('track-fill');
    const btnText = analyzeBtn.querySelector('.btn-text');
    const btnLoader = analyzeBtn.querySelector('.btn-loader');

    let selectedFile = null;
    const STEP_MAP = { face_detection: 1, embedding: 2, web_search: 3, verification: 4, blockchain: 5 };
    const STEP_LABELS = {
        face_detection: 'Face detection',
        embedding: 'Embedding',
        web_search: 'Web search',
        verification: 'Verification',
        blockchain: 'Blockchain'
    };

    // Upload interactions
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', (e) => { e.preventDefault(); uploadArea.classList.add('dragover'); });
    uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', (e) => { if (e.target.files.length) handleFile(e.target.files[0]); });
    changeImageBtn.addEventListener('click', resetUpload);
    retryBtn.addEventListener('click', resetUpload);
    analyzeBtn.addEventListener('click', () => { if (selectedFile) analyzeImage(); });

    // Subtle cursor light for desktop.
    const glow = document.querySelector('.cursor-glow');
    if (glow && window.matchMedia('(pointer:fine)').matches) {
        window.addEventListener('pointermove', (e) => {
            glow.style.left = `${e.clientX - 170}px`;
            glow.style.top = `${e.clientY - 170}px`;
        }, { passive: true });
    }

    function handleFile(file) {
        const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/gif'];
        if (!allowedTypes.includes(file.type)) {
            showError('Invalid file type. Please upload JPG, PNG, WebP, BMP, or GIF.');
            return;
        }
        if (file.size > 16 * 1024 * 1024) {
            showError('File too large. Maximum size is 16MB.');
            return;
        }

        selectedFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            uploadArea.style.display = 'none';
            uploadPreview.style.display = 'flex';
            analyzeBtn.disabled = false;
            consoleStatus.textContent = 'Ready to scan.';
            consoleDetail.textContent = 'Image loaded. Start the five-stage identity signal pipeline.';
            resultStamp.textContent = 'READY';
        };
        reader.readAsDataURL(file);
    }

    function resetUpload() {
        selectedFile = null;
        window._uploadedImageUrl = null;
        fileInput.value = '';
        uploadArea.style.display = 'flex';
        uploadPreview.style.display = 'none';
        analyzeBtn.disabled = true;
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
        hideAllSections();
        resetSteps();
        resetResults();
        updateScanner(0);
        updateConsole('Ready to scan.', 'Upload a face image to start the identity signal pipeline.');
    }

    async function analyzeImage() {
        analyzeBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';
        hideAllSections();
        progressSection.style.display = 'none';
        resultsSection.style.display = 'block';
        logOutput.innerHTML = '';
        resetSteps();
        resetResults();
        updateScanner(3);
        updateConsole('Signal acquired.', 'Running face detection, web discovery, verification and blockchain anchoring.');
        resultStamp.textContent = 'RUNNING';
        document.getElementById('results-section').scrollIntoView({ behavior: 'smooth', block: 'start' });

        const formData = new FormData();
        formData.append('image', selectedFile);
        formData.append('tamper_demo', 'true');
        formData.append('skip_blockchain', 'false');
        formData.append('mock_search', 'false');

        try {
            const response = await fetch('/api/analyze', { method: 'POST', body: formData });
            if (!response.ok || !response.body) throw new Error(`Server returned ${response.status}`);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const chunks = buffer.split('\n\n');
                buffer = chunks.pop() || '';
                chunks.forEach(parseSSEChunk);
            }
            if (buffer.trim()) parseSSEChunk(buffer);
        } catch (error) {
            showError(`Network error: ${error.message}`);
        } finally {
            analyzeBtn.disabled = !selectedFile;
            btnText.style.display = 'inline';
            btnLoader.style.display = 'none';
        }
    }

    function parseSSEChunk(chunk) {
        let eventType = null;
        let eventData = '';
        chunk.split('\n').forEach((line) => {
            if (line.startsWith('event: ')) eventType = line.slice(7).trim();
            else if (line.startsWith('data: ')) eventData += line.slice(6);
        });
        if (!eventType) return;
        try { handleSSEEvent(eventType, JSON.parse(eventData)); }
        catch (e) { console.warn('SSE parse error:', e); }
    }

    function handleSSEEvent(type, data) {
        switch (type) {
            case 'step_started':
                markStepActive(data.step);
                setStepStatus(data.step, 'Running...', 'running');
                appendLog(`[${data.step}] ${data.message}`, 'info');
                updateConsole(STEP_LABELS[data.step] || 'Pipeline step running.', data.message || 'Working...');
                break;
            case 'step_progress':
                appendLog(`  ${data.message}`, 'progress');
                consoleDetail.textContent = data.message || consoleDetail.textContent;
                break;
            case 'step_done':
                markStepCompleted(data.step);
                setStepStatus(data.step, 'Done', 'success');
                appendLog(`[${data.step}] Completed`, 'success');
                displayStepResult(data.step, data.data || {});
                updateConsole(doneStatusFor(data.step, data.data || {}), doneDetailFor(data.step, data.data || {}));
                updateScanner(progressFor(data.step));
                break;
            case 'step_error':
                markStepError(data.step);
                setStepStatus(data.step, 'Error', 'error');
                appendLog(`[${data.step}] ${data.error}`, 'error');
                if (data.evaluated_candidates) displayVerification({ status: 'error', matched: false, evaluated_candidates: data.evaluated_candidates });
                updateConsole('Pipeline needs attention.', data.error || 'A pipeline step failed.');
                resultStamp.textContent = 'ATTENTION';
                break;
            case 'pipeline_done':
                window._uploadedImageUrl = data.uploaded_image_url || null;
                if (!data.success && data.error) {
                    showError(data.error);
                } else {
                    updateScanner(100);
                    resultStamp.textContent = 'COMPLETE';
                    updateConsole('Signal complete.', 'Local evidence was processed through the configured pipeline.');
                }
                break;
        }
    }

    function doneStatusFor(step, data) {
        if (step === 'verification') return data.matched ? 'Identity match found.' : 'No verified match.';
        if (step === 'blockchain') return data.verified ? 'Proof anchored on-chain.' : 'Blockchain step completed.';
        if (step === 'web_search') return 'Web candidates discovered.';
        if (step === 'face_detection') return 'Face detected.';
        return 'Signal encoded.';
    }
    function doneDetailFor(step, data) {
        if (step === 'verification') return data.matched ? `${(data.similarity * 100).toFixed(1)}% similarity · ${data.confidence_tier || 'MATCH'}` : 'No candidate passed the current threshold.';
        if (step === 'blockchain') return data.verified ? 'The local fingerprint matches the on-chain record.' : 'Review the blockchain output below.';
        if (step === 'web_search') return `${data.candidates_count || 0} candidates · ${data.social_count || 0} social sources`;
        if (step === 'face_detection') return `${data.faces_count || 0} face(s) detected · ${(data.confidence * 100 || 0).toFixed(1)}% detector confidence`;
        return `512-dim embedding · L2 norm ${Number(data.norm || 0).toFixed(4)}`;
    }
    function progressFor(step) { return ({ face_detection: 20, embedding: 36, web_search: 58, verification: 79, blockchain: 100 })[step] || 0; }

    function updateConsole(title, detail) {
        consoleStatus.textContent = title;
        consoleDetail.textContent = detail;
    }

    function updateScanner(percent) {
        if (scannerProgress) scannerProgress.textContent = `${String(Math.round(percent)).padStart(2, '0')}%`;
        if (scannerFill) scannerFill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
        if (trackFill) trackFill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
    }

    function appendLog(message, level = 'info') {
        const line = document.createElement('div');
        line.className = `log-line log-${level}`;
        line.textContent = message;
        logOutput.appendChild(line);
        logOutput.scrollTop = logOutput.scrollHeight;
    }

    function markStepActive(stepName) {
        const num = STEP_MAP[stepName];
        const el = num ? document.getElementById(`step-${num}`) : null;
        if (el) { el.classList.remove('completed', 'error'); el.classList.add('active'); }
        updateDecorStep(stepName, 'running');
    }
    function markStepCompleted(stepName) {
        const num = STEP_MAP[stepName];
        const el = num ? document.getElementById(`step-${num}`) : null;
        if (el) { el.classList.remove('active', 'error'); el.classList.add('completed'); }
        updateDecorStep(stepName, 'done');
    }
    function markStepError(stepName) {
        const num = STEP_MAP[stepName];
        const el = num ? document.getElementById(`step-${num}`) : null;
        if (el) { el.classList.remove('active', 'completed'); el.classList.add('error'); }
        updateDecorStep(stepName, 'error');
    }

    function updateDecorStep(stepName, state) {
        const mini = document.querySelector(`[data-mini-step="${stepName}"]`);
        if (mini) mini.textContent = state === 'done' ? '✓' : state === 'error' ? '×' : '…';
        const consoleStep = document.querySelector(`[data-console-step="${stepName}"]`);
        if (consoleStep) {
            consoleStep.classList.remove('done', 'running');
            const badge = consoleStep.querySelector('b');
            if (state === 'done') { consoleStep.classList.add('done'); badge.textContent = '✓'; }
            else if (state === 'running') { consoleStep.classList.add('running'); badge.textContent = '…'; }
            else if (state === 'error') { badge.textContent = '×'; }
            else { badge.textContent = '—'; }
        }
        const flow = document.querySelector(`.workflow-step[data-step="${stepName}"]`);
        if (flow) {
            flow.classList.remove('active', 'completed');
            if (state === 'running') flow.classList.add('active');
            if (state === 'done') flow.classList.add('completed');
        }
    }

    function setStepStatus(stepName, text, level) {
        const el = $(`status-${stepName}`);
        if (el) { el.textContent = text; el.className = `status-badge ${level}`; }
    }

    function displayStepResult(stepName, data) {
        switch (stepName) {
            case 'face_detection': displayFaceDetection(data); break;
            case 'embedding': displayEmbedding(data); break;
            case 'web_search': displayWebSearch(data); break;
            case 'verification': displayVerification(data); break;
            case 'blockchain': displayBlockchain(data); break;
        }
    }

    function resetSteps() {
        for (let i = 1; i <= 5; i++) {
            const step = document.getElementById(`step-${i}`);
            if (step) step.classList.remove('active', 'completed', 'error');
        }
        Object.keys(STEP_MAP).forEach((step) => updateDecorStep(step, 'idle'));
    }

    function resetResults() {
        const steps = ['face-detection', 'embedding', 'web-search', 'verification', 'blockchain'];
        steps.forEach((step) => {
            const status = $(`status-${step}`);
            const body = $(`body-${step}`);
            const card = $(`result-${step}`);
            if (status) { status.textContent = 'Pending'; status.className = 'status-badge pending'; }
            if (body) body.innerHTML = '<div class="loading-spinner"></div>';
            if (card) card.classList.remove('success', 'error');
        });
    }

    function hideAllSections() {
        if (progressSection) progressSection.style.display = 'none';
        if (resultsSection) resultsSection.style.display = 'none';
        if (errorSection) errorSection.style.display = 'none';
    }

    function showError(message) {
        if (errorMessage) errorMessage.textContent = message;
        if (errorSection) errorSection.style.display = 'block';
    }

    function displayFaceDetection(data) {
        const body = $('body-face-detection');
        const card = $('result-face-detection');
        if (data.status === 'success') {
            card.classList.add('success');
            let imageLinkHtml = '';
            if (window._uploadedImageUrl) {
                const fullUrl = window.location.origin + window._uploadedImageUrl;
                imageLinkHtml = `<div class="data-item" style="grid-column:1/-1"><div class="data-label">Uploaded image</div><div class="data-value"><a href="${escapeHtml(fullUrl)}" target="_blank" rel="noopener">Open source image ↗</a></div></div>`;
            }
            body.innerHTML = `<div class="data-grid"><div class="data-item"><div class="data-label">Faces</div><div class="data-value">${data.faces_count}</div></div><div class="data-item"><div class="data-label">Confidence</div><div class="data-value success">${(data.confidence*100).toFixed(1)}%</div></div><div class="data-item"><div class="data-label">Bounding box</div><div class="data-value">[${data.bbox.join(', ')}]</div></div><div class="data-item"><div class="data-label">Embedding dim.</div><div class="data-value">${data.embedding_dim}</div></div>${imageLinkHtml}</div>`;
        } else { card.classList.add('error'); body.innerHTML = `<p class="data-value error">Face detection failed.</p>`; }
    }

    function displayEmbedding(data) {
        const body = $('body-embedding');
        const card = $('result-embedding');
        if (data.status === 'success') {
            card.classList.add('success');
            body.innerHTML = `<div class="data-grid"><div class="data-item"><div class="data-label">Embedding norm</div><div class="data-value success">${Number(data.norm).toFixed(4)}</div></div><div class="data-item"><div class="data-label">Status</div><div class="data-value success">L2 normalized</div></div></div>`;
        } else { card.classList.add('error'); body.innerHTML = `<p class="data-value error">Embedding failed.</p>`; }
    }

    function displayWebSearch(data) {
        const body = $('body-web-search');
        const card = $('result-web-search');
        if (data.status === 'success') {
            card.classList.add('success');
            const candidates = (data.candidates || []).slice(0, 12);
            const candidatesHtml = candidates.length ? `<div class="candidates-grid">${candidates.map((c) => `<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener" class="candidate-card"><div class="candidate-img-wrap">${c.thumbnail ? `<img src="${escapeHtml(c.thumbnail)}" alt="${escapeHtml(c.title || '')}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" /><div class="candidate-img-fallback" style="display:none">NO PREVIEW</div>` : `<div class="candidate-img-fallback">NO PREVIEW</div>`}</div><div class="candidate-info"><div class="candidate-source">${escapeHtml(c.source || 'unknown')}${c.is_social ? '<span class="social-badge">social</span>' : ''}</div><div class="candidate-title">${escapeHtml((c.title || '').slice(0, 60))}${(c.title || '').length > 60 ? '…' : ''}</div></div></a>`).join('')}</div>` : '<p class="data-value">No candidates returned.</p>';
            body.innerHTML = `<div class="data-grid"><div class="data-item"><div class="data-label">Candidates</div><div class="data-value">${data.candidates_count}</div></div><div class="data-item"><div class="data-label">Social sources</div><div class="data-value success">${data.social_count}</div></div></div>${candidatesHtml}`;
        } else { card.classList.add('error'); body.innerHTML = `<p class="data-value error">Web search failed.</p>`; }
    }

    function displayVerification(data) {
        const body = $('body-verification');
        const card = $('result-verification');
        const evalHtml = data.evaluated_candidates && data.evaluated_candidates.length ? `<table class="candidates-table"><thead><tr><th>#</th><th>Source</th><th>Similarity</th><th>Tier</th></tr></thead><tbody>${data.evaluated_candidates.map((c,i)=>`<tr><td>${i+1}</td><td>${escapeHtml(c.source||'Unknown')}</td><td>${c.has_face ? (c.similarity*100).toFixed(1)+'%' : 'No face'}</td><td>${escapeHtml(c.confidence_tier||'—')}</td></tr>`).join('')}</tbody></table>` : '';
        if (data.status === 'success' && data.matched) {
            card.classList.add('success');
            body.innerHTML = `<div class="verification-badge">✓ MATCH FOUND</div><div class="data-grid"><div class="data-item"><div class="data-label">Platform</div><div class="data-value">${escapeHtml(data.platform)}</div></div><div class="data-item"><div class="data-label">Similarity</div><div class="data-value success">${(data.similarity*100).toFixed(1)}%</div></div><div class="data-item"><div class="data-label">Confidence</div><div class="data-value">${escapeHtml(data.confidence_tier || 'MATCH')}</div></div><div class="data-item"><div class="data-label">Matched post</div><div class="data-value"><a href="${escapeHtml(data.url)}" target="_blank" rel="noopener">Open source ↗</a></div></div></div>${evalHtml}`;
        } else {
            card.classList.add('error');
            body.innerHTML = `<div class="verification-badge failed">× NO MATCH</div><p class="data-value error">No candidate passed the verification threshold.</p>${evalHtml}`;
        }
    }

    function matchedLinkBanner(data, itemClass) {
        if (!data || !data.matched_url) return '';
        const labelCls = itemClass === 'blockchain-item' ? 'label' : 'data-label';
        const valueCls = itemClass === 'blockchain-item' ? 'value' : 'data-value';
        const pct = (data.matched_similarity !== undefined && data.matched_similarity !== null)
            ? ` · ${(Number(data.matched_similarity) * 100).toFixed(1)}%` : '';
        const tier = data.confidence_tier ? ` · ${escapeHtml(data.confidence_tier)}` : '';
        return `<div class="${itemClass}" style="grid-column:1/-1"><div class="${labelCls}">Final matched link · ${escapeHtml(data.matched_platform || '')}${pct}${tier}</div><div class="${valueCls}"><a href="${escapeHtml(data.matched_url)}" target="_blank" rel="noopener">Open matched source ↗</a></div></div>`;
    }

    function displayBlockchain(data) {
        const body = $('body-blockchain');
        const card = $('result-blockchain');
        if (data.status === 'skipped') { $('status-blockchain').textContent = 'Skipped'; $('status-blockchain').className = 'status-badge skipped'; body.innerHTML = `<div class="data-grid">${matchedLinkBanner(data, 'data-item')}</div><p class="data-value">Blockchain verification skipped.</p>`; return; }
        if (data.status === 'success') {
            card.classList.add('success');
            let tamperHtml = '';
            if (data.tamper_demo) tamperHtml = `<div class="tamper-demo"><h4>Tamper detection</h4><p>Changing the canonical payload changes its fingerprint.</p><div class="tamper-comparison"><div class="tamper-item original"><div class="label">Original</div><div class="hash">${escapeHtml(data.tamper_demo.original_hash)}</div></div><div class="tamper-item tampered"><div class="label">Tampered</div><div class="hash">${escapeHtml(data.tamper_demo.tampered_hash)}</div></div></div><p style="margin-top:8px;color:${data.tamper_demo.hashes_equal?'#9a7217':'#b65b63'};font-weight:600">${data.tamper_demo.hashes_equal ? 'Hashes match.' : 'Hashes differ — tamper detected.'}</p></div>`;
            body.innerHTML = `<div class="verification-badge ${data.verified ? '' : 'failed'}">${data.verified ? '✓ VERIFIED ON-CHAIN' : '× VERIFICATION FAILED'}</div><div class="blockchain-info">${matchedLinkBanner(data, 'blockchain-item')}<div class="blockchain-item"><div class="label">Network</div><div class="value">${escapeHtml(data.network)} (${escapeHtml(String(data.chain_id))})</div></div><div class="blockchain-item"><div class="label">Content hash</div><div class="value hash">${escapeHtml(data.content_hash)}</div></div><div class="blockchain-item"><div class="label">Transaction</div><div class="value"><a href="${escapeHtml(data.explorer_url)}" target="_blank" rel="noopener">${escapeHtml((data.tx_hash||'').slice(0,22))}…</a></div></div><div class="blockchain-item"><div class="label">Block</div><div class="value">${escapeHtml(String(data.block_number))}</div></div><div class="blockchain-item"><div class="label">Contract</div><div class="value hash">${escapeHtml(data.contract_address)}</div></div><div class="blockchain-item"><div class="label">Explorer</div><div class="value"><a href="${escapeHtml(data.explorer_url)}" target="_blank" rel="noopener">View on PolygonScan ↗</a></div></div></div>${tamperHtml}`;
        } else { card.classList.add('error'); body.innerHTML = '<p class="data-value error">Blockchain verification failed.</p>'; }
    }

    function escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    resetSteps();
    resetResults();
});
