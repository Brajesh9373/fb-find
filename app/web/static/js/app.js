// Face → Web → Blockchain - Frontend Logic (SSE streaming)

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const uploadPreview = document.getElementById('upload-preview');
    const previewImage = document.getElementById('preview-image');
    const changeImageBtn = document.getElementById('change-image');
    const analyzeBtn = document.getElementById('analyze-btn');
    const btnText = analyzeBtn.querySelector('.btn-text');
    const btnLoader = analyzeBtn.querySelector('.btn-loader');
    const progressSection = document.getElementById('progress-section');
    const resultsSection = document.getElementById('results-section');
    const errorSection = document.getElementById('error-section');
    const errorMessage = document.getElementById('error-message');
    const retryBtn = document.getElementById('retry-btn');
    const logOutput = document.getElementById('log-output');

    let selectedFile = null;
    const STEP_MAP = { face_detection: 1, embedding: 2, web_search: 3, verification: 4, blockchain: 5 };

    // File Upload Handlers
    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    changeImageBtn.addEventListener('click', () => {
        resetUpload();
    });

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
            uploadPreview.style.display = 'block';
            analyzeBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    function resetUpload() {
        selectedFile = null;
        window._uploadedImageUrl = null;
        fileInput.value = '';
        uploadArea.style.display = 'block';
        uploadPreview.style.display = 'none';
        analyzeBtn.disabled = true;
        hideAllSections();
    }

    analyzeBtn.addEventListener('click', () => {
        if (!selectedFile) return;
        analyzeImage();
    });

    retryBtn.addEventListener('click', () => {
        resetUpload();
    });

    async function analyzeImage() {
        analyzeBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';

        hideAllSections();
        progressSection.style.display = 'block';
        resultsSection.style.display = 'flex';
        if (logOutput) logOutput.innerHTML = '';

        resetSteps();
        resetResults();

        const formData = new FormData();
        formData.append('image', selectedFile);
        formData.append('tamper_demo', document.getElementById('tamper-demo')?.checked ?? false);
        formData.append('skip_blockchain', document.getElementById('skip-blockchain')?.checked ?? false);
        formData.append('mock_search', document.getElementById('mock-search')?.checked ?? false);

        try {
            const response = await fetch('/api/analyze', { method: 'POST', body: formData });
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                let eventType = null;
                let eventData = '';

                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        eventData += line.slice(6);
                    } else if (line === '' && eventType) {
                        try {
                            const parsed = JSON.parse(eventData);
                            handleSSEEvent(eventType, parsed);
                        } catch (e) {
                            console.warn('SSE parse error:', e);
                        }
                        eventType = null;
                        eventData = '';
                    }
                }
            }
        } catch (error) {
            showError('Network error: ' + error.message);
        } finally {
            analyzeBtn.disabled = false;
            btnText.style.display = 'inline';
            btnLoader.style.display = 'none';
        }
    }

    function handleSSEEvent(type, data) {
        switch (type) {
            case 'step_started':
                markStepActive(data.step);
                appendLog(`[${data.step}] ${data.message}`, 'info');
                setStepStatus(data.step, 'Running...', 'running');
                break;

            case 'step_progress':
                appendLog(`  ${data.message}`, 'progress');
                break;

            case 'step_done':
                markStepCompleted(data.step);
                setStepStatus(data.step, 'Done', 'success');
                appendLog(`[${data.step}] Completed`, 'success');
                displayStepResult(data.step, data.data);
                break;

            case 'step_error':
                markStepError(data.step);
                setStepStatus(data.step, 'Error', 'error');
                appendLog(`[${data.step}] ${data.error}`, 'error');
                if (data.evaluated_candidates) {
                    displayVerification({ status: 'error', matched: false, evaluated_candidates: data.evaluated_candidates });
                }
                break;

            case 'pipeline_done':
                window._uploadedImageUrl = data.uploaded_image_url || null;
                if (!data.success && data.error) {
                    showError(data.error);
                }
                break;
        }
    }

    function appendLog(message, level) {
        if (!logOutput) return;
        const line = document.createElement('div');
        line.className = `log-line log-${level}`;
        line.textContent = message;
        logOutput.appendChild(line);
        logOutput.scrollTop = logOutput.scrollHeight;
    }

    function markStepActive(stepName) {
        const num = STEP_MAP[stepName];
        if (!num) return;
        const el = document.getElementById(`step-${num}`);
        if (el) {
            el.classList.remove('completed', 'error');
            el.classList.add('active');
        }
    }

    function markStepCompleted(stepName) {
        const num = STEP_MAP[stepName];
        if (!num) return;
        const el = document.getElementById(`step-${num}`);
        if (el) {
            el.classList.remove('active', 'error');
            el.classList.add('completed');
        }
    }

    function markStepError(stepName) {
        const num = STEP_MAP[stepName];
        if (!num) return;
        const el = document.getElementById(`step-${num}`);
        if (el) {
            el.classList.remove('active', 'completed');
            el.classList.add('error');
        }
    }

    function setStepStatus(stepName, text, level) {
        const el = document.getElementById(`status-${stepName}`);
        if (el) {
            el.textContent = text;
            el.className = `status-badge ${level}`;
        }
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
            step.classList.remove('active', 'completed', 'error');
        }
    }

    function resetResults() {
        const steps = ['face-detection', 'embedding', 'web-search', 'verification', 'blockchain'];
        steps.forEach(step => {
            const status = document.getElementById(`status-${step}`);
            const body = document.getElementById(`body-${step}`);
            const card = document.getElementById(`result-${step}`);

            status.textContent = 'Pending';
            status.className = 'status-badge pending';
            body.innerHTML = '<div class="loading-spinner"></div>';
            card.classList.remove('success', 'error');
        });
    }

    function hideAllSections() {
        progressSection.style.display = 'none';
        resultsSection.style.display = 'none';
        errorSection.style.display = 'none';
    }

    function showError(message) {
        hideAllSections();
        errorSection.style.display = 'block';
        errorMessage.textContent = message;
    }

    function displayFaceDetection(data) {
        const body = document.getElementById('body-face-detection');
        const card = document.getElementById('result-face-detection');

        if (data.status === 'success') {
            card.classList.add('success');

            let imageLinkHtml = '';
            if (window._uploadedImageUrl) {
                const fullUrl = window.location.origin + window._uploadedImageUrl;
                imageLinkHtml = `
                    <div class="data-item" style="grid-column: 1 / -1;">
                        <div class="data-label">Image Link</div>
                        <div class="data-value">
                            <a href="${fullUrl}" target="_blank" rel="noopener" style="color: var(--primary); text-decoration: none; word-break: break-all;">
                                ${fullUrl}
                            </a>
                            <button onclick="navigator.clipboard.writeText('${fullUrl}')" style="margin-left: 8px; padding: 2px 8px; border: 1px solid var(--border); border-radius: 4px; background: var(--surface); color: var(--text); cursor: pointer; font-size: 0.75rem;">Copy</button>
                        </div>
                    </div>
                `;
            }

            body.innerHTML = `
                <div class="data-grid">
                    <div class="data-item">
                        <div class="data-label">Faces Detected</div>
                        <div class="data-value">${data.faces_count}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Confidence</div>
                        <div class="data-value success">${(data.confidence * 100).toFixed(1)}%</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Bounding Box</div>
                        <div class="data-value">[${data.bbox.join(', ')}]</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Embedding Dimension</div>
                        <div class="data-value">${data.embedding_dim}</div>
                    </div>
                    ${imageLinkHtml}
                </div>
            `;
        } else {
            card.classList.add('error');
            body.innerHTML = `<p class="data-value error">Face detection failed</p>`;
        }
    }

    function displayEmbedding(data) {
        const body = document.getElementById('body-embedding');
        const card = document.getElementById('result-embedding');

        if (data.status === 'success') {
            card.classList.add('success');
            body.innerHTML = `
                <div class="data-grid">
                    <div class="data-item">
                        <div class="data-label">Embedding Norm</div>
                        <div class="data-value success">${data.norm.toFixed(4)}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Status</div>
                        <div class="data-value success">L2 Normalized</div>
                    </div>
                </div>
            `;
        } else {
            card.classList.add('error');
            body.innerHTML = `<p class="data-value error">Embedding failed</p>`;
        }
    }

    function displayWebSearch(data) {
        const body = document.getElementById('body-web-search');
        const card = document.getElementById('result-web-search');

        if (data.status === 'success') {
            card.classList.add('success');

            let candidatesHtml = '';
            if (data.candidates && data.candidates.length > 0) {
                candidatesHtml = `
                    <div class="candidates-grid">
                        ${data.candidates.slice(0, 12).map((c, i) => `
                            <a href="${escapeHtml(c.url)}" target="_blank" rel="noopener" class="candidate-card">
                                <div class="candidate-img-wrap">
                                    ${c.thumbnail
                                        ? `<img src="${escapeHtml(c.thumbnail)}" alt="${escapeHtml(c.title || '')}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><div class="candidate-img-fallback" style="display:none">📷</div>`
                                        : `<div class="candidate-img-fallback">📷</div>`
                                    }
                                </div>
                                <div class="candidate-info">
                                    <div class="candidate-source">${escapeHtml(c.source || 'Unknown')}${c.is_social ? ' <span class="social-badge">Social</span>' : ''}</div>
                                    <div class="candidate-title">${escapeHtml((c.title || '').substring(0, 60))}${c.title && c.title.length > 60 ? '...' : ''}</div>
                                </div>
                            </a>
                        `).join('')}
                    </div>
                `;
            }

            body.innerHTML = `
                <div class="data-grid">
                    <div class="data-item">
                        <div class="data-label">Total Candidates</div>
                        <div class="data-value">${data.candidates_count}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Social Media</div>
                        <div class="data-value success">${data.social_count}</div>
                    </div>
                </div>
                ${candidatesHtml}
            `;
        } else {
            card.classList.add('error');
            body.innerHTML = `<p class="data-value error">Web search failed</p>`;
        }
    }

    function displayVerification(data) {
        const body = document.getElementById('body-verification');
        const card = document.getElementById('result-verification');

        if (data.status === 'success' && data.matched) {
            card.classList.add('success');

            let evalHtml = '';
            if (data.evaluated_candidates && data.evaluated_candidates.length > 0) {
                evalHtml = `
                    <table class="candidates-table" style="margin-top: 1rem;">
                        <thead>
                            <tr><th>#</th><th>Source</th><th>Similarity</th><th>Tier</th></tr>
                        </thead>
                        <tbody>
                            ${data.evaluated_candidates.map((c, i) => `
                                <tr>
                                    <td>${i + 1}</td>
                                    <td>${escapeHtml(c.source || 'Unknown')}</td>
                                    <td>${c.has_face ? (c.similarity * 100).toFixed(1) + '%' : 'No face'}</td>
                                    <td>${c.confidence_tier}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            }

            body.innerHTML = `
                <div class="verification-badge verified">
                    MATCH FOUND
                </div>
                <div class="data-grid">
                    <div class="data-item">
                        <div class="data-label">Platform</div>
                        <div class="data-value">${escapeHtml(data.platform)}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Similarity</div>
                        <div class="data-value success">${(data.similarity * 100).toFixed(1)}%</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Confidence</div>
                        <div class="data-value ${data.confidence_tier === 'HIGH' ? 'success' : ''}">${data.confidence_tier}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">URL</div>
                        <div class="data-value">
                            <a href="${escapeHtml(data.url)}" target="_blank" rel="noopener" style="color: var(--primary); text-decoration: none;">
                                ${escapeHtml((data.url || '').substring(0, 50))}...
                            </a>
                        </div>
                    </div>
                </div>
                ${evalHtml}
            `;
        } else {
            card.classList.add('error');

            let evalHtml = '';
            if (data.evaluated_candidates && data.evaluated_candidates.length > 0) {
                evalHtml = `
                    <table class="candidates-table" style="margin-top: 1rem;">
                        <thead>
                            <tr><th>#</th><th>Source</th><th>Similarity</th><th>Tier</th></tr>
                        </thead>
                        <tbody>
                            ${data.evaluated_candidates.map((c, i) => `
                                <tr>
                                    <td>${i + 1}</td>
                                    <td>${escapeHtml(c.source || 'Unknown')}</td>
                                    <td>${c.has_face ? (c.similarity * 100).toFixed(1) + '%' : 'No face'}</td>
                                    <td>${c.confidence_tier}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            }

            body.innerHTML = `
                <div class="verification-badge failed">
                    NO MATCH
                </div>
                <p class="data-value error">No candidate passed verification threshold</p>
                ${evalHtml}
            `;
        }
    }

    function displayBlockchain(data) {
        const body = document.getElementById('body-blockchain');
        const card = document.getElementById('result-blockchain');

        if (data.status === 'skipped') {
            document.getElementById('status-blockchain').textContent = 'Skipped';
            document.getElementById('status-blockchain').className = 'status-badge skipped';
            body.innerHTML = `<p class="data-value">Blockchain verification skipped</p>`;
            return;
        }

        if (data.status === 'success') {
            card.classList.add('success');

            let tamperHtml = '';
            if (data.tamper_demo) {
                tamperHtml = `
                    <div class="tamper-demo">
                        <h4>Tamper Detection Demo</h4>
                        <p style="color: var(--text-secondary); margin-bottom: 1rem;">
                            Demonstrates why blockchain matters: modifying data changes the hash
                        </p>
                        <div class="tamper-comparison">
                            <div class="tamper-item original">
                                <div class="label">Original Hash</div>
                                <div class="hash">${data.tamper_demo.original_hash}</div>
                            </div>
                            <div class="tamper-item tampered">
                                <div class="label">Tampered Hash</div>
                                <div class="hash">${data.tamper_demo.tampered_hash}</div>
                            </div>
                        </div>
                        <p style="margin-top: 1rem; color: var(--error); font-weight: 600;">
                            ${data.tamper_demo.hashes_equal ? 'Hashes match (unexpected)' : 'Hashes differ - tamper detected!'}
                        </p>
                    </div>
                `;
            }

            body.innerHTML = `
                <div class="verification-badge ${data.verified ? 'verified' : 'failed'}">
                    ${data.verified ? 'VERIFIED ON-CHAIN' : 'VERIFICATION FAILED'}
                </div>
                <div class="blockchain-info">
                    <div class="blockchain-item">
                        <div class="label">Network</div>
                        <div class="value">${escapeHtml(data.network)} (${data.chain_id})</div>
                    </div>
                    <div class="blockchain-item">
                        <div class="label">Content Hash</div>
                        <div class="value">${data.content_hash}</div>
                    </div>
                    <div class="blockchain-item">
                        <div class="label">Transaction</div>
                        <div class="value">
                            <a href="${data.explorer_url}" target="_blank" rel="noopener" style="color: var(--primary); text-decoration: none;">
                                ${data.tx_hash.substring(0, 20)}...
                            </a>
                        </div>
                    </div>
                    <div class="blockchain-item">
                        <div class="label">Block Number</div>
                        <div class="value">${data.block_number}</div>
                    </div>
                    <div class="blockchain-item">
                        <div class="label">Contract</div>
                        <div class="value">${data.contract_address}</div>
                    </div>
                    <div class="blockchain-item">
                        <div class="label">Explorer</div>
                        <div class="value">
                            <a href="${data.explorer_url}" target="_blank" rel="noopener" style="color: var(--primary); text-decoration: none;">
                                View on PolygonScan
                            </a>
                        </div>
                    </div>
                </div>
                ${tamperHtml}
            `;
        } else {
            card.classList.add('error');
            body.innerHTML = `<p class="data-value error">Blockchain verification failed</p>`;
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
