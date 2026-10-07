document.addEventListener("DOMContentLoaded", () => {

    // ========================================================
    // ELEMENTS
    // ========================================================

    const video = document.getElementById(
        "attendanceVideo"
    );

    const canvas = document.getElementById(
        "attendanceCanvas"
    );

    const startButton = document.getElementById(
        "startAttendanceCamera"
    );

    const stopButton = document.getElementById(
        "stopAttendanceCamera"
    );

    const faceStatus = document.getElementById(
        "faceStatus"
    );

    const recognitionStatus = document.getElementById(
        "recognitionStatus"
    );

    const confidenceStatus = document.getElementById(
        "confidenceStatus"
    );

    const attendanceStatus = document.getElementById(
        "attendanceStatus"
    );

    const cameraMessage = document.getElementById(
        "cameraMessage"
    );


    // ========================================================
    // CHECK REQUIRED ELEMENTS
    // ========================================================

    if (!video) {
        console.error(
            "attendanceVideo element not found."
        );
        return;
    }

    if (!canvas) {
        console.error(
            "attendanceCanvas element not found."
        );
        return;
    }

    if (!startButton) {
        console.error(
            "startAttendanceCamera button not found."
        );
        return;
    }

    if (!stopButton) {
        console.error(
            "stopAttendanceCamera button not found."
        );
        return;
    }


    // ========================================================
    // VARIABLES
    // ========================================================

    let stream = null;

    let recognitionTimer = null;

    let recognitionRunning = false;

    let attendanceCompleted = false;


    // ========================================================
    // BUTTON EVENTS
    // ========================================================

    startButton.addEventListener(
        "click",
        startCamera
    );

    stopButton.addEventListener(
        "click",
        stopCamera
    );


    // ========================================================
    // START CAMERA
    // ========================================================

    async function startCamera() {

        try {

            stopCamera();

            if (
                !navigator.mediaDevices ||
                !navigator.mediaDevices.getUserMedia
            ) {

                throw new Error(
                    "Camera API is not available in this browser."
                );
            }


            // ------------------------------------------------
            // CAMERA ACCESS
            // ------------------------------------------------

            stream =
                await navigator.mediaDevices.getUserMedia({

                    video: {

                        width: {
                            ideal: 1280
                        },

                        height: {
                            ideal: 720
                        },

                        facingMode: "user"

                    },

                    audio: false

                });


            // ------------------------------------------------
            // VIDEO
            // ------------------------------------------------

            video.srcObject = stream;

            await video.play();


            // ------------------------------------------------
            // RESET STATUS
            // ------------------------------------------------

            attendanceCompleted = false;

            faceStatus.textContent =
                "Camera active";

            recognitionStatus.textContent =
                "Searching";

            confidenceStatus.textContent =
                "0%";

            attendanceStatus.textContent =
                "Not marked";

            cameraMessage.textContent =
                "Looking for a registered student face...";


            // ------------------------------------------------
            // START RECOGNITION
            // ------------------------------------------------

            startRecognitionLoop();

        }

        catch (error) {

            console.error(
                "Camera error:",
                error
            );

            cameraMessage.textContent =
                error.message ||
                "Unable to access camera.";

            faceStatus.textContent =
                "Camera error";
        }
    }


    // ========================================================
    // START RECOGNITION LOOP
    // ========================================================

    function startRecognitionLoop() {

        stopRecognitionLoop();

        recognitionTimer =
            setInterval(
                recognizeCurrentFrame,
                1500
            );

        recognizeCurrentFrame();
    }


    // ========================================================
    // STOP RECOGNITION LOOP
    // ========================================================

    function stopRecognitionLoop() {

        if (recognitionTimer) {

            clearInterval(
                recognitionTimer
            );

            recognitionTimer = null;
        }
    }


    // ========================================================
    // RECOGNIZE CURRENT CAMERA FRAME
    // ========================================================

    async function recognizeCurrentFrame() {

        // Do not send multiple requests
        // at the same time.

        if (recognitionRunning) {
            return;
        }


        // Attendance already completed.

        if (attendanceCompleted) {
            return;
        }


        // Camera not running.

        if (!stream) {
            return;
        }


        // Video must have dimensions.

        if (
            !video.videoWidth ||
            !video.videoHeight
        ) {

            return;
        }


        recognitionRunning = true;


        try {

            // ------------------------------------------------
            // SET CANVAS SIZE
            // ------------------------------------------------

            canvas.width =
                video.videoWidth;

            canvas.height =
                video.videoHeight;


            // ------------------------------------------------
            // DRAW CAMERA FRAME
            // ------------------------------------------------

            const context =
                canvas.getContext(
                    "2d",
                    {
                        willReadFrequently: true
                    }
                );


            context.drawImage(
                video,
                0,
                0,
                canvas.width,
                canvas.height
            );


            // ------------------------------------------------
            // CONVERT TO IMAGE
            // ------------------------------------------------

            const image =
                canvas.toDataURL(
                    "image/jpeg",
                    0.85
                );


            faceStatus.textContent =
                "Checking face...";


            // ------------------------------------------------
            // CSRF
            // ------------------------------------------------

            const csrfToken =
                window.CSRF_TOKEN || "";


            if (!csrfToken) {

                throw new Error(
                    "Security token is missing. "
                    + "Refresh the page."
                );
            }


            // ------------------------------------------------
            // SEND TO FLASK
            // ------------------------------------------------

            const response =
                await fetch(
                    "/api/recognize-face",
                    {

                        method: "POST",

                        credentials: "same-origin",

                        cache: "no-store",

                        headers: {

                            "Content-Type":
                                "application/json",

                            "Accept":
                                "application/json",

                            "X-CSRFToken":
                                csrfToken

                        },

                        body: JSON.stringify({
                            image: image
                        })

                    }
                );


            // ------------------------------------------------
            // READ RESPONSE
            // ------------------------------------------------

            const contentType =
                response.headers.get(
                    "content-type"
                ) || "";


            let result;


            if (
                contentType.includes(
                    "application/json"
                )
            ) {

                result =
                    await response.json();

            }

            else {

                const text =
                    await response.text();

                console.error(
                    "Unexpected server response:",
                    text
                );

                throw new Error(
                    "Server returned an unexpected response."
                );
            }


            // ------------------------------------------------
            // HTTP ERROR
            // ------------------------------------------------

            if (!response.ok) {

                throw new Error(
                    result.message ||
                    "Recognition request failed."
                );
            }


            // =================================================
            // UNKNOWN FACE
            // =================================================

            if (
                !result.recognized
            ) {

                const failureMessage =
                    result.message ||
                    "No registered student face found.";

                if (failureMessage.includes("No face detected")) {
                    faceStatus.textContent =
                        "No face detected";
                } else if (failureMessage.includes("Multiple faces detected")) {
                    faceStatus.textContent =
                        "Multiple faces detected";
                } else {
                    faceStatus.textContent =
                        "Face not recognized";
                }

                recognitionStatus.textContent =
                    "Unknown";

                confidenceStatus.textContent =
                    `${Number(
                        result.confidence || 0
                    ).toFixed(2)}%`;

                attendanceStatus.textContent =
                    "Not marked";


                // Show actual server reason

                cameraMessage.textContent =
                    failureMessage;


                // Debug information

                console.log(
                    "Face not recognized:",
                    {
                        message:
                            result.message,

                        distance:
                            result.face_distance,

                        confidence:
                            result.confidence
                    }
                );


                return;
            }


            // =================================================
            // RECOGNIZED STUDENT
            // =================================================

            const student =
                result.student || {};


            faceStatus.textContent =
                "Face recognized";


            recognitionStatus.textContent =
                student.name ||
                "Recognized";


            confidenceStatus.textContent =
                `${Number(
                    result.confidence || 0
                ).toFixed(2)}%`;


            console.log(
                "Student recognized:",
                {
                    student:
                        student,

                    distance:
                        result.face_distance,

                    confidence:
                        result.confidence,

                    attendanceMarked:
                        result.attendance_marked,

                    alreadyMarked:
                        result.already_marked
                }
            );


            // =================================================
            // ALREADY MARKED
            // =================================================

            if (
                result.already_marked
            ) {

                attendanceStatus.textContent =
                    "Already marked";


                cameraMessage.textContent =
                    "Attendance already marked today.";


                attendanceCompleted =
                    true;


                stopRecognitionLoop();

                stopCamera();

                return;
            }


            // =================================================
            // ATTENDANCE MARKED
            // =================================================

            if (
                result.attendance_marked
            ) {

                attendanceStatus.textContent =
                    "Present";


                cameraMessage.textContent =
                    result.message ||
                    "Attendance marked successfully.";


                attendanceCompleted =
                    true;


                stopRecognitionLoop();

                stopCamera();

                return;
            }


            // =================================================
            // RECOGNIZED BUT NOT MARKED
            // =================================================

            attendanceStatus.textContent =
                "Not marked";


            cameraMessage.textContent =
                result.message ||
                "Student recognized but attendance "
                + "was not marked.";


        }

        catch (error) {

            console.error(
                "Recognition error:",
                error
            );


            cameraMessage.textContent =
                error.message ||
                "Recognition failed.";


        }

        finally {

            recognitionRunning =
                false;
        }
    }


    // ========================================================
    // STOP CAMERA
    // ========================================================

    function stopCamera() {

        stopRecognitionLoop();


        if (stream) {

            stream
                .getTracks()
                .forEach(
                    track => track.stop()
                );

            stream = null;
        }


        video.srcObject = null;


        if (faceStatus) {

            faceStatus.textContent =
                "Camera stopped";
        }
    }


    // ========================================================
    // PAGE CLOSE
    // ========================================================

    window.addEventListener(
        "beforeunload",
        stopCamera
    );

});