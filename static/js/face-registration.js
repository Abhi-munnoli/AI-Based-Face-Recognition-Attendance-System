document.addEventListener("DOMContentLoaded", () => {
    const video = document.getElementById("faceVideo");
    const canvas = document.getElementById("faceCanvas");
    const faceImage = document.getElementById("faceImage");
    const startCameraBtn = document.getElementById("startCameraBtn");
    const captureFaceBtn = document.getElementById("captureFaceBtn");
    const retakeFaceBtn = document.getElementById("retakeFaceBtn");
    const facePreview = document.getElementById("facePreview");
    const facePreviewPlaceholder = document.getElementById("facePreviewPlaceholder");
    const faceStatus = document.getElementById("faceStatus");
    const registerStudentBtn = document.getElementById("registerStudentBtn");
    const form = document.getElementById("studentRegistrationForm");

    let stream = null;

    captureFaceBtn.disabled = true;
    retakeFaceBtn.disabled = true;
    registerStudentBtn.disabled = true;

    startCameraBtn.addEventListener("click", async () => {
        try {
            stopCamera();

            if (!navigator.mediaDevices?.getUserMedia) {
                throw new Error("Camera API is not available in this browser.");
            }

            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: "user"
                },
                audio: false
            });

            video.srcObject = stream;
            await video.play();

            captureFaceBtn.disabled = false;
            faceStatus.textContent = "Camera ready. Keep exactly one face visible and centered.";
            faceStatus.className = "face-status success";
        } catch (error) {
            console.error("Camera error:", error);
            faceStatus.textContent = "Unable to access camera. Please allow camera permission.";
            faceStatus.className = "face-status error";
        }
    });

    captureFaceBtn.addEventListener("click", () => {
        if (!stream) {
            faceStatus.textContent = "Please open the camera first.";
            return;
        }

        if (!video.videoWidth || !video.videoHeight) {
            faceStatus.textContent = "Camera is not ready yet.";
            return;
        }

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const context = canvas.getContext("2d", { willReadFrequently: true });
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        const imageData = canvas.toDataURL("image/jpeg", 0.90);
        faceImage.value = imageData;

        facePreview.src = imageData;
        facePreview.style.display = "block";
        facePreviewPlaceholder.style.display = "none";

        registerStudentBtn.disabled = false;
        retakeFaceBtn.disabled = false;
        captureFaceBtn.disabled = true;

        faceStatus.textContent = "Face captured. Click Register Student.";
        faceStatus.className = "face-status success";

        stopCamera();
    });

    retakeFaceBtn.addEventListener("click", async () => {
        faceImage.value = "";
        facePreview.removeAttribute("src");
        facePreview.style.display = "none";
        facePreviewPlaceholder.style.display = "block";
        registerStudentBtn.disabled = true;
        retakeFaceBtn.disabled = true;
        faceStatus.textContent = "Opening camera. Capture the face again.";
        faceStatus.className = "face-status";

        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: "user"
                },
                audio: false
            });

            video.srcObject = stream;
            await video.play();
            captureFaceBtn.disabled = false;
        } catch (error) {
            console.error(error);
            faceStatus.textContent = "Unable to restart camera.";
            faceStatus.className = "face-status error";
        }
    });

    form.addEventListener("submit", (event) => {
        if (!faceImage.value) {
            event.preventDefault();
            faceStatus.textContent = "Please capture the student's face before registering.";
            faceStatus.className = "face-status error";
            return;
        }

        registerStudentBtn.disabled = true;
        registerStudentBtn.textContent = "Registering...";
    });

    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        video.srcObject = null;
    }

    window.addEventListener("beforeunload", stopCamera);
});
