// Face → Web → Blockchain - Frontend Logic

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

    let selectedFile = null;

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
        // Validate file type
        const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/gif'];
        if (!allowedTypes.includes(file.type)) {
            showError('Invalid file type. Please upload JPG, PNG, WebP, BMP, or GIF.');
            return;
        }

        // Validate file size (16MB)
        if (file.size > 16 * 1024 * 1024) {
            showError('File too large. Maximum size is 16MB.');
            return;
        }

        selectedFile = file;

        // Show preview
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
        fileInput.value = '';
        uploadArea.style.display = 'block';
        uploadPreview.style.display = 'none';
        analyzeBtn.disabled = true;
        hideAllSections();
    }

    // Analyze Button
    analyzeBtn.addEventListener('click', () => {
        if (!selectedFile) return;
        analyzeImage();
    });

    retryBtn.addEventListener('click', () => {
        resetUpload();
    });

    async function analyzeImage() {
        // Show loading state
        analyzeBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';

        // Show progress section
        hideAllSections();
        progressSection.style.display = 'block';
        resultsSection.style.display = 'flex';

        // Reset all steps
        resetSteps();
        resetResults();

        // Prepare form data
        const formData = new FormData();
        formData.append('image', selectedFile);
        formData.append('tamper_demo', document.getElementById('tamper-demo').checked);
        formData.append('skip_blockchain', document.getElementById('skip-blockchain').checked);

        try {
            // Simulate progress updates
            simulateProgress();

            // Make API call
            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (data.success) {
                displayResults(data.steps);
            } else {
                showError(data.error || 'Analysis failed');
            }
        } catch (error) {
            showError('Network error: ' + error.message);
        } finally {
            // Reset button state
            analyzeBtn.disabled = false;
            btnText.style.display = 'inline';
            btnLoader.style.display = 'none';
        }
    }

    function simulateProgress() {
        const steps = ['step-1', 'step-2', 'step-3', 'step-4', 'step-5'];
        let currentStep = 0;

        const interval = setInterval(() => {
            if (currentStep < steps.length) {
                // Mark previous step as completed
                if (currentStep > 0) {
                    document.getElementById(steps[currentStep - 1]).classList.remove('active');
                    document.getElementById(steps[currentStep - 1]).classList.add('completed');
                }
                // Mark current step as active
                document.getElementById(steps[currentStep]).classList.add('active');
                currentStep++;
            } else {
                clearInterval(interval);
            }
        }, 500);
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

    function displayResults(steps) {
        // Mark all steps as completed
        for (let i = 1; i <= 5; i++) {
            const step = document.getElementById(`step-${i}`);
            step.classList.remove('active');
            step.classList.add('completed');
        }

        // Display each step result
        displayFaceDetection(steps.face_detection);
        displayEmbedding(steps.embedding);
        displayWebSearch(steps.web_search);
        displayVerification(steps.verification);
        displayBlockchain(steps.blockchain);
    }

    function displayFaceDetection(data) {
        const status = document.getElementById('status-face-detection');
        const body = document.getElementById('body-face-detection');
        const card = document.getElementById('result-face-detection');

        if (data.status === 'success') {
            status.textContent = 'Success';
            status.className = 'status-badge success';
            card.classList.add('success');

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
                </div>
            `;
        } else {
            status.textContent = 'Error';
            status.className = 'status-badge error';
            card.classList.add('error');
            body.innerHTML = `<p class="data-value error">Face detection failed</p>`;
        }
    }

    function displayEmbedding(data) {
        const status = document.getElementById('status-embedding');
        const body = document.getElementById('body-embedding');
        const card = document.getElementById('result-embedding');

        if (data.status === 'success') {
            status.textContent = 'Success';
            status.className = 'status-badge success';
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
            status.textContent = 'Error';
            status.className = 'status-badge error';
            card.classList.add('error');
            body.innerHTML = `<p class="data-value error">Embedding failed</p>`;
        }
    }

    function displayWebSearch(data) {
        const status = document.getElementById('status-web-search');
        const body = document.getElementById('body-web-search');
        const card = document.getElementById('result-web-search');

        if (data.status === 'success') {
            status.textContent = 'Success';
            status.className = 'status-badge success';
            card.classList.add('success');

            let candidatesHtml = '';
            if (data.candidates && data.candidates.length > 0) {
                candidatesHtml = `
                    <table class="candidates-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Source</th>
                                <th>Title</th>
                                <th>Type</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.candidates.slice(0, 8).map((c, i) => `
                                <tr>
                                    <td>${i + 1}</td>
                                    <td>${escapeHtml(c.source || 'Unknown')}</td>
                                    <td>${escapeHtml((c.title || '').substring(0, 50))}${c.title && c.title.length > 50 ? '...' : ''}</td>
                                    <td>${c.is_social ? '<span class="social-badge">Social</span>' : 'Web'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
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
            status.textContent = 'Error';
            status.className = 'status-badge error';
            card.classList.add('error');
            body.innerHTML = `<p class="data-value error">Web search failed</p>`;
        }
    }

    function displayVerification(data) {
        const status = document.getElementById('status-verification');
        const body = document.getElementById('body-verification');
        const card = document.getElementById('result-verification');

        if (data.status === 'success' && data.matched) {
            status.textContent = 'Matched';
            status.className = 'status-badge success';
            card.classList.add('success');

            body.innerHTML = `
                <div class="verification-badge verified">
                    ✓ MATCH FOUND
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
                        <div class="data-label">Title</div>
                        <div class="data-value">${escapeHtml((data.title || '').substring(0, 60))}</div>
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
            `;
        } else {
            status.textContent = 'No Match';
            status.className = 'status-badge error';
            card.classList.add('error');
            body.innerHTML = `
                <div class="verification-badge failed">
                    ✗ NO MATCH
                </div>
                <p class="data-value error">No candidate passed verification threshold</p>
            `;
        }
    }

    function displayBlockchain(data) {
        const status = document.getElementById('status-blockchain');
        const body = document.getElementById('body-blockchain');
        const card = document.getElementById('result-blockchain');

        if (data.status === 'skipped') {
            status.textContent = 'Skipped';
            status.className = 'status-badge skipped';
            body.innerHTML = `<p class="data-value">Blockchain verification skipped</p>`;
            return;
        }

        if (data.status === 'success') {
            status.textContent = 'Success';
            status.className = 'status-badge success';
            card.classList.add('success');

            let tamperHtml = '';
            if (data.tamper_demo) {
                tamperHtml = `
                    <div class="tamper-demo">
                        <h4>🔍 Tamper Detection Demo</h4>
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
                            ${data.tamper_demo.hashes_equal ? '⚠️ Hashes match (unexpected)' : '✓ Hashes differ - tamper detected!'}
                        </p>
                    </div>
                `;
            }

            body.innerHTML = `
                <div class="verification-badge ${data.verified ? 'verified' : 'failed'}">
                    ${data.verified ? '✓ VERIFIED ON-CHAIN' : '✗ VERIFICATION FAILED'}
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
                                View on PolygonScan →
                            </a>
                        </div>
                    </div>
                </div>
                ${tamperHtml}
            `;
        } else {
            status.textContent = 'Error';
            status.className = 'status-badge error';
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
