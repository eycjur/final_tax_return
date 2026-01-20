/**
 * Camera functionality for the tax return application
 * Uses HTML5 getUserMedia API for capturing photos
 */

let videoStream = null;

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', function() {
    setupCameraHandlers();
});

// Re-setup handlers when modal content changes (Dash renders dynamically)
const observer = new MutationObserver(function(mutations) {
    setupCameraHandlers();
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});

function setupCameraHandlers() {
    const btnCamera = document.getElementById('btn-camera');
    const btnCapture = document.getElementById('btn-capture');
    const btnCancel = document.getElementById('btn-camera-cancel');

    if (btnCamera && !btnCamera.hasAttribute('data-listener')) {
        btnCamera.setAttribute('data-listener', 'true');
        btnCamera.addEventListener('click', startCamera);
    }

    if (btnCapture && !btnCapture.hasAttribute('data-listener')) {
        btnCapture.setAttribute('data-listener', 'true');
        btnCapture.addEventListener('click', capturePhoto);
    }

    if (btnCancel && !btnCancel.hasAttribute('data-listener')) {
        btnCancel.setAttribute('data-listener', 'true');
        btnCancel.addEventListener('click', stopCamera);
    }
}

async function startCamera() {
    const cameraContainer = document.getElementById('camera-container');
    const video = document.getElementById('camera-video');

    if (!cameraContainer || !video) {
        console.error('Camera elements not found');
        return;
    }

    // Check if getUserMedia is available
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('カメラ機能を使用するには、localhostまたはHTTPSでアクセスしてください。\n\nURL: http://localhost:8050');
        return;
    }

    try {
        // Request camera access with preference for back camera on mobile
        const constraints = {
            video: {
                facingMode: { ideal: 'environment' },
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        };

        videoStream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = videoStream;
        cameraContainer.style.display = 'block';

        // Hide the camera button while camera is active
        const btnCamera = document.getElementById('btn-camera');
        if (btnCamera) {
            btnCamera.style.display = 'none';
        }
    } catch (err) {
        console.error('Camera access error:', err);
        if (err.name === 'NotAllowedError') {
            alert('カメラへのアクセスが拒否されました。ブラウザの設定でカメラを許可してください。');
        } else if (err.name === 'NotFoundError') {
            alert('カメラが見つかりません。カメラが接続されているか確認してください。');
        } else {
            alert('カメラにアクセスできません: ' + err.message);
        }
    }
}

function capturePhoto() {
    const video = document.getElementById('camera-video');
    const canvas = document.getElementById('camera-canvas');
    const preview = document.getElementById('camera-preview');

    if (!video || !canvas || !preview) {
        console.error('Required elements not found');
        return;
    }

    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw video frame to canvas
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    // Convert to base64 data URL
    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);

    // Show preview
    preview.innerHTML = `
        <img src="${dataUrl}" class="preview-image" alt="Captured photo">
        <p class="text-success mt-2"><i class="fas fa-check-circle me-1"></i>撮影完了</p>
    `;

    // Store the captured image data in Dash stores
    // We need to dispatch a custom event that Dash can pick up
    const filename = 'camera_' + new Date().toISOString().replace(/[:.]/g, '-') + '.jpg';

    // Update Dash stores via clientside callback
    if (window.dash_clientside) {
        // Store the data in a way Dash can access
        const uploadPreview = document.getElementById('upload-preview');
        if (uploadPreview) {
            uploadPreview.innerHTML = `
                <img src="${dataUrl}" class="preview-image" alt="Captured photo">
            `;
        }

        // Trigger update to Dash stores
        const storeData = document.querySelector('[id="store-attachment-data"]');
        const storeName = document.querySelector('[id="store-attachment-name"]');

        if (storeData && storeName) {
            // Dispatch custom event with the captured data
            const event = new CustomEvent('camera-capture', {
                detail: {
                    data: dataUrl,
                    filename: filename
                }
            });
            document.dispatchEvent(event);
        }
    }

    // Stop camera after capture
    stopCamera();
}

function stopCamera() {
    const cameraContainer = document.getElementById('camera-container');
    const video = document.getElementById('camera-video');
    const btnCamera = document.getElementById('btn-camera');

    // Stop all video tracks
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }

    // Clear video source
    if (video) {
        video.srcObject = null;
    }

    // Hide camera container
    if (cameraContainer) {
        cameraContainer.style.display = 'none';
    }

    // Show camera button again
    if (btnCamera) {
        btnCamera.style.display = 'inline-flex';
    }
}

// Listen for camera capture events and update Dash stores
document.addEventListener('camera-capture', function(e) {
    const { data, filename } = e.detail;

    // Find the upload component and simulate an upload
    const uploadArea = document.querySelector('.upload-area');
    if (uploadArea) {
        // Create a fake upload event that Dash will process
        const fakeFile = {
            contents: data,
            filename: filename
        };

        // The upload-preview will already be updated by capturePhoto
        // We need to manually trigger the Dash callback by updating hidden inputs

        // Create and dispatch input event for store-attachment-data
        const dataInput = document.createElement('input');
        dataInput.type = 'hidden';
        dataInput.id = 'camera-data-input';
        dataInput.value = data;

        const nameInput = document.createElement('input');
        nameInput.type = 'hidden';
        nameInput.id = 'camera-name-input';
        nameInput.value = filename;

        // Remove old inputs if they exist
        const oldData = document.getElementById('camera-data-input');
        const oldName = document.getElementById('camera-name-input');
        if (oldData) oldData.remove();
        if (oldName) oldName.remove();

        document.body.appendChild(dataInput);
        document.body.appendChild(nameInput);
    }
});

// Clientside callback helper for Dash
if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.camera = {
    getCapturedData: function() {
        const dataInput = document.getElementById('camera-data-input');
        return dataInput ? dataInput.value : null;
    },
    getCapturedFilename: function() {
        const nameInput = document.getElementById('camera-name-input');
        return nameInput ? nameInput.value : null;
    }
};
