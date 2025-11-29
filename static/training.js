/**
 * Training Page JavaScript
 * Handles all interactions for training and model management
 */

// Global state
let captureInterval = null;
let trainingInterval = null;
let selectedCamera = null;

// ==================== INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', function() {
    loadCameras();
    loadDatasets();
    loadModels();
    updateDetectionStatus();
    
    // Auto-refresh every 5 seconds
    setInterval(updateDetectionStatus, 5000);
    
    // Check if capturing
    setInterval(updateCaptureStatus, 1000);
});

// ==================== CAMERA MANAGEMENT ====================

async function loadCameras() {
    try {
        const response = await fetch('/api/cameras');
        const cameras = await response.json();
        
        const cameraList = document.getElementById('camera-list');
        cameraList.innerHTML = '';
        
        cameras.forEach(camera => {
            const option = document.createElement('div');
            option.className = 'radio-option';
            option.innerHTML = `
                <input type="radio" name="camera" value="${camera.id}" 
                       onchange="selectCamera('${camera.id}')">
                <div>
                    <div style="font-weight: 600;">${camera.name}</div>
                    <div style="font-size: 12px; color: #666;">${camera.resolution} - ${camera.type}</div>
                </div>
            `;
            cameraList.appendChild(option);
        });
        
        // Load current camera
        const currentResponse = await fetch('/api/camera/current');
        const currentCamera = await currentResponse.json();
        
        if (currentCamera && currentCamera.id) {
            document.querySelector(`input[value="${currentCamera.id}"]`).checked = true;
            document.querySelector(`input[value="${currentCamera.id}"]`).parentElement.classList.add('selected');
            document.getElementById('active-camera').textContent = currentCamera.name;
            selectedCamera = currentCamera.id;
        }
        
    } catch (error) {
        console.error('Error loading cameras:', error);
    }
}

async function selectCamera(cameraId) {
    try {
        // Remove all selected classes
        document.querySelectorAll('.radio-option').forEach(opt => {
            opt.classList.remove('selected');
        });
        
        // Add selected class
        const selected = document.querySelector(`input[value="${cameraId}"]`).parentElement;
        selected.classList.add('selected');
        
        const response = await fetch('/api/camera/select', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({camera_id: cameraId})
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('Error: ' + result.error);
            return;
        }
        
        selectedCamera = cameraId;
        document.getElementById('active-camera').textContent = result.camera.name;
        
        // Refresh preview
        document.getElementById('preview-feed').src = '/api/training/preview?' + Date.now();
        
        showAlert('Camera selected: ' + result.camera.name, 'success');
        
    } catch (error) {
        console.error('Error selecting camera:', error);
        alert('Failed to select camera');
    }
}

async function addCustomCamera() {
    const name = document.getElementById('custom-camera-name').value.trim();
    const url = document.getElementById('custom-camera-url').value.trim();
    
    if (!name || !url) {
        alert('Please enter both name and URL');
        return;
    }
    
    try {
        const response = await fetch('/api/camera/add', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name, url})
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('Error: ' + result.error);
            return;
        }
        
        document.getElementById('custom-camera-name').value = '';
        document.getElementById('custom-camera-url').value = '';
        
        loadCameras();
        showAlert('Camera added: ' + name, 'success');
        
    } catch (error) {
        console.error('Error adding camera:', error);
        alert('Failed to add camera');
    }
}

// ==================== DETECTION CONTROL ====================

async function updateDetectionStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();
        
        const statusElement = document.getElementById('detection-status');
        const startBtn = document.getElementById('start-detection-btn');
        const stopBtn = document.getElementById('stop-detection-btn');
        
        if (status.active) {
            statusElement.innerHTML = '<span class="status-indicator active"></span> Running';
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } else {
            statusElement.innerHTML = '<span class="status-indicator inactive"></span> Stopped';
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
        
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

async function startDetection() {
    try {
        const response = await fetch('/api/start', {method: 'POST'});
        const result = await response.json();
        
        if (result.status === 'started') {
            showAlert('Detection started', 'success');
            updateDetectionStatus();
        }
    } catch (error) {
        console.error('Error starting detection:', error);
        alert('Failed to start detection');
    }
}

async function stopDetection() {
    try {
        const response = await fetch('/api/stop', {method: 'POST'});
        const result = await response.json();
        
        if (result.status === 'stopped') {
            showAlert('Detection stopped', 'info');
            updateDetectionStatus();
        }
    } catch (error) {
        console.error('Error stopping detection:', error);
        alert('Failed to stop detection');
    }
}

// ==================== DATA COLLECTION ====================

async function startAutoCapture() {
    const personName = document.getElementById('person-name').value.trim();
    const target = parseInt(document.getElementById('target-count').value);
    
    if (!personName) {
        alert('Please enter a person name');
        return;
    }
    
    if (!selectedCamera) {
        alert('Please select a camera first');
        return;
    }
    
    try {
        // Start capture
        const response = await fetch('/api/training/start-capture', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                person_name: personName,
                camera_source: selectedCamera,
                auto: true,
                target: target
            })
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('Error: ' + result.error);
            return;
        }
        
        // Update UI
        document.getElementById('start-capture-btn').disabled = true;
        document.getElementById('manual-capture-btn').disabled = false;
        document.getElementById('stop-capture-btn').disabled = false;
        document.getElementById('capture-target').textContent = target;
        
        showAlert(`Auto-capture started for ${personName}`, 'success');
        
        // Start auto-capture interval (every 500ms)
        captureInterval = setInterval(async () => {
            await captureFrame();
        }, 500);
        
    } catch (error) {
        console.error('Error starting capture:', error);
        alert('Failed to start capture');
    }
}

async function manualCapture() {
    await captureFrame();
}

async function captureFrame() {
    try {
        const response = await fetch('/api/training/capture-frame', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.error) {
            console.error('Capture error:', result.error);
            return;
        }
        
        // Update progress
        document.getElementById('capture-count').textContent = result.captured;
        const progress = (result.captured / result.target) * 100;
        document.getElementById('capture-progress').style.width = progress + '%';
        document.getElementById('capture-progress').textContent = Math.round(progress) + '%';
        
        // Check if complete
        if (result.complete) {
            stopCapture();
            showAlert(result.message, 'success');
            loadDatasets();
        }
        
    } catch (error) {
        console.error('Error capturing frame:', error);
    }
}

async function stopCapture() {
    try {
        // Clear interval
        if (captureInterval) {
            clearInterval(captureInterval);
            captureInterval = null;
        }
        
        const response = await fetch('/api/training/stop-capture', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        // Reset UI
        document.getElementById('start-capture-btn').disabled = false;
        document.getElementById('manual-capture-btn').disabled = true;
        document.getElementById('stop-capture-btn').disabled = true;
        
        showAlert('Capture stopped', 'info');
        loadDatasets();
        
    } catch (error) {
        console.error('Error stopping capture:', error);
    }
}

async function clearCapture() {
    if (!confirm('Clear current capture progress?')) {
        return;
    }
    
    await stopCapture();
    
    // Reset counters
    document.getElementById('capture-count').textContent = '0';
    document.getElementById('capture-progress').style.width = '0%';
    document.getElementById('capture-progress').textContent = '0%';
}

async function updateCaptureStatus() {
    try {
        const response = await fetch('/api/training/capture-status');
        const status = await response.json();
        
        if (status.capturing) {
            document.getElementById('capture-count').textContent = status.count;
            const progress = (status.count / status.target) * 100;
            document.getElementById('capture-progress').style.width = progress + '%';
            document.getElementById('capture-progress').textContent = Math.round(progress) + '%';
        }
    } catch (error) {
        // Silently fail
    }
}

// ==================== DATASET MANAGEMENT ====================

async function loadDatasets() {
    try {
        const response = await fetch('/api/training/datasets');
        const datasets = await response.json();
        
        const datasetList = document.getElementById('dataset-list');
        const trainingDatasets = document.getElementById('training-datasets');
        
        if (datasets.length === 0) {
            datasetList.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">No datasets yet. Start collecting!</div>';
            trainingDatasets.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">No datasets available</div>';
            return;
        }
        
        // Update dataset list
        datasetList.innerHTML = '';
        datasets.forEach(dataset => {
            const statusClass = dataset.count >= 200 ? 'complete' : 'incomplete';
            const statusIcon = dataset.count >= 200 ? '✅' : '⚠️';
            
            const item = document.createElement('div');
            item.className = `dataset-item ${statusClass}`;
            item.innerHTML = `
                <div class="dataset-info">
                    <div class="dataset-name">${statusIcon} ${dataset.person} (${dataset.camera})</div>
                    <div class="dataset-meta">${dataset.count} images - Created: ${new Date(dataset.created).toLocaleString()}</div>
                </div>
                <div class="dataset-actions">
                    <button class="btn btn-danger btn-small" onclick="deleteDataset('${dataset.name}')">
                        🗑️ Delete
                    </button>
                </div>
            `;
            datasetList.appendChild(item);
        });
        
        // Update training checkboxes
        trainingDatasets.innerHTML = '';
        datasets.forEach(dataset => {
            const checkbox = document.createElement('div');
            checkbox.className = 'checkbox-option';
            
            const canTrain = dataset.count >= 50;
            const warningText = dataset.count < 200 ? ' (needs more images)' : '';
            
            checkbox.innerHTML = `
                <input type="checkbox" id="dataset-${dataset.name}" value="${dataset.name}" 
                       ${canTrain ? '' : 'disabled'} ${canTrain ? 'checked' : ''}>
                <label for="dataset-${dataset.name}">
                    ${dataset.person} (${dataset.camera}) - ${dataset.count} images${warningText}
                </label>
            `;
            trainingDatasets.appendChild(checkbox);
        });
        
    } catch (error) {
        console.error('Error loading datasets:', error);
    }
}

async function deleteDataset(datasetName) {
    if (!confirm('Delete this dataset? This cannot be undone!')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/training/dataset/${datasetName}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.status === 'deleted') {
            showAlert('Dataset deleted', 'success');
            loadDatasets();
        }
    } catch (error) {
        console.error('Error deleting dataset:', error);
        alert('Failed to delete dataset');
    }
}

async function refreshDatasets() {
    await loadDatasets();
    showAlert('Datasets refreshed', 'info');
}

// ==================== MODEL TRAINING ====================

async function startTraining() {
    const modelName = document.getElementById('model-name').value.trim();
    const epochs = parseInt(document.getElementById('train-epochs').value);
    const batch = parseInt(document.getElementById('train-batch').value);
    const imgsz = parseInt(document.getElementById('train-imgsz').value);
    
    if (!modelName) {
        alert('Please enter a model name');
        return;
    }
    
    // Get selected datasets
    const selectedDatasets = [];
    document.querySelectorAll('#training-datasets input[type="checkbox"]:checked').forEach(checkbox => {
        const datasetName = checkbox.value;
        // Find dataset info
        const label = checkbox.nextElementSibling.textContent;
        const match = label.match(/(.*?) \((.*?)\) - (\d+) images/);
        if (match) {
            selectedDatasets.push({
                name: datasetName,
                person: match[1],
                camera: match[2],
                count: parseInt(match[3])
            });
        }
    });
    
    if (selectedDatasets.length === 0) {
        alert('Please select at least one dataset');
        return;
    }
    
    if (!confirm(`Start training model "${modelName}" with ${selectedDatasets.length} datasets?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/training/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                model_name: modelName,
                datasets: selectedDatasets,
                epochs: epochs,
                batch: batch,
                imgsz: imgsz
            })
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('Error: ' + result.error);
            return;
        }
        
        document.getElementById('start-training-btn').disabled = true;
        document.getElementById('training-progress-container').style.display = 'block';
        
        showAlert(`Training started: ${modelName}`, 'success');
        
        // Start monitoring training progress
        trainingInterval = setInterval(updateTrainingProgress, 2000);
        
    } catch (error) {
        console.error('Error starting training:', error);
        alert('Failed to start training');
    }
}

async function updateTrainingProgress() {
    try {
        const response = await fetch('/api/training/status');
        const status = await response.json();
        
        document.getElementById('training-status').textContent = status.status;
        document.getElementById('training-loss').textContent = status.loss.toFixed(4);
        document.getElementById('training-map').textContent = status.map.toFixed(3);
        document.getElementById('training-eta').textContent = status.eta;
        
        if (status.total_epochs > 0) {
            const progress = (status.epoch / status.total_epochs) * 100;
            document.getElementById('training-progress').style.width = progress + '%';
            document.getElementById('training-progress').textContent = `Epoch ${status.epoch}/${status.total_epochs}`;
        }
        
        if (status.status === 'complete') {
            clearInterval(trainingInterval);
            document.getElementById('start-training-btn').disabled = false;
            showAlert('Training complete!', 'success');
            loadModels();
        } else if (status.status === 'failed') {
            clearInterval(trainingInterval);
            document.getElementById('start-training-btn').disabled = false;
            showAlert('Training failed: ' + status.error, 'danger');
        }
        
    } catch (error) {
        console.error('Error checking training progress:', error);
    }
}

// ==================== MODEL MANAGEMENT ====================

async function loadModels() {
    try {
        const response = await fetch('/api/training/models');
        const models = await response.json();
        
        const modelList = document.getElementById('model-list');
        
        if (models.length === 0) {
            modelList.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">No models yet. Train your first model!</div>';
            document.getElementById('active-model').textContent = 'No model loaded';
            document.getElementById('model-classes').textContent = 'N/A';
            return;
        }
        
        modelList.innerHTML = '';
        
        models.forEach((model, index) => {
            const isActive = index === 0; // First model is active (for now)
            
            const item = document.createElement('div');
            item.className = `model-item ${isActive ? 'active' : ''}`;
            item.innerHTML = `
                <div class="model-header">
                    <div class="model-name">${model.name}</div>
                    ${isActive ? '<div class="model-badge">ACTIVE</div>' : ''}
                </div>
                <div class="model-details">
                    <div>📅 ${new Date(model.created).toLocaleString()}</div>
                    <div>👥 Classes: ${model.classes.join(', ')}</div>
                    <div>📹 Cameras: ${model.cameras.join(', ')}</div>
                    <div>📊 Accuracy: ${(model.metrics.map * 100).toFixed(1)}%</div>
                    <div>🔄 Epochs: ${model.epochs}</div>
                    <div>💾 Size: ${model.size_mb.toFixed(1)} MB</div>
                </div>
                <div class="model-actions">
                    ${!isActive ? `<button class="btn btn-primary btn-small" onclick="loadModel('${model.name}')">🔄 Load Model</button>` : ''}
                    <button class="btn btn-danger btn-small" onclick="deleteModel('${model.name}')">🗑️ Delete</button>
                </div>
            `;
            modelList.appendChild(item);
            
            if (isActive) {
                document.getElementById('active-model').textContent = model.name;
                document.getElementById('model-classes').textContent = model.classes.join(', ');
            }
        });
        
    } catch (error) {
        console.error('Error loading models:', error);
    }
}

async function loadModel(modelName) {
    if (!confirm(`Load model "${modelName}"? This will stop detection if running.`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/training/load-model', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({model_name: modelName})
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert('Error: ' + result.error);
            return;
        }
        
        showAlert(`Model loaded: ${modelName}`, 'success');
        loadModels();
        updateDetectionStatus();
        
    } catch (error) {
        console.error('Error loading model:', error);
        alert('Failed to load model');
    }
}

async function deleteModel(modelName) {
    if (!confirm(`Delete model "${modelName}"? This cannot be undone!`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/training/model/${modelName}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.status === 'deleted') {
            showAlert('Model deleted', 'success');
            loadModels();
        }
    } catch (error) {
        console.error('Error deleting model:', error);
        alert('Failed to delete model');
    }
}

async function refreshModels() {
    await loadModels();
    showAlert('Models refreshed', 'info');
}

// ==================== UTILITY FUNCTIONS ====================

function showAlert(message, type = 'info') {
    const statusText = document.getElementById('capture-status-text');
    statusText.className = `alert alert-${type}`;
    statusText.textContent = message;
    statusText.style.display = 'block';
    
    setTimeout(() => {
        statusText.style.display = 'none';
    }, 3000);
}