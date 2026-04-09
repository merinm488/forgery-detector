(function () {
    'use strict';

    var dropZone = document.getElementById('drop-zone');
    var fileInput = document.getElementById('file-input');
    var uploadForm = document.getElementById('upload-form');
    var previewSection = document.getElementById('preview-section');
    var previewImage = document.getElementById('preview-image');
    var previewName = document.getElementById('preview-name');
    var removeBtn = document.getElementById('remove-btn');
    var analyzeBtn = document.getElementById('analyze-btn');

    if (!dropZone) return; // Not on upload page

    // Click to browse
    dropZone.addEventListener('click', function () {
        fileInput.click();
    });

    // Drag events
    dropZone.addEventListener('dragover', function (e) {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', function () {
        dropZone.classList.remove('dragover');
    });
    dropZone.addEventListener('drop', function (e) {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            showPreview(e.dataTransfer.files[0]);
        }
    });

    // File input change
    fileInput.addEventListener('change', function () {
        if (fileInput.files.length) {
            showPreview(fileInput.files[0]);
        }
    });

    // Remove file
    removeBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        fileInput.value = '';
        previewSection.style.display = 'none';
        dropZone.style.display = '';
        analyzeBtn.disabled = true;
    });

    function showPreview(file) {
        var reader = new FileReader();
        reader.onload = function (e) {
            previewImage.src = e.target.result;
            previewName.textContent = file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)';
            previewSection.style.display = '';
            dropZone.style.display = 'none';
            analyzeBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    // Color the score bars on report page
    document.querySelectorAll('.score-bar').forEach(function (bar) {
        var score = parseFloat(bar.getAttribute('data-score') || '0');
        if (score >= 0.6) bar.style.background = '#ef4444';
        else if (score >= 0.4) bar.style.background = '#f59e0b';
        else if (score >= 0.2) bar.style.background = '#eab308';
        else bar.style.background = '#22c55e';
    });

    // Color the risk score ring
    var ring = document.querySelector('.risk-score-ring');
    if (ring) {
        var score = parseFloat(ring.getAttribute('data-score') || '0');
        if (score >= 0.8) ring.style.background = '#dc2626';
        else if (score >= 0.6) ring.style.background = '#ef4444';
        else if (score >= 0.4) ring.style.background = '#f59e0b';
        else if (score >= 0.2) ring.style.background = '#eab308';
        else ring.style.background = '#22c55e';
    }
})();
