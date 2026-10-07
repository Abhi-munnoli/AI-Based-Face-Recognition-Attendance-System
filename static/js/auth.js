import {
    initializeApp
} from "https://www.gstatic.com/firebasejs/11.0.2/firebase-app.js";

import {
    getAuth,
    signInWithEmailAndPassword,
    signOut
} from "https://www.gstatic.com/firebasejs/11.0.2/firebase-auth.js";


/* ============================================================
   FIREBASE CONFIG
============================================================ */

async function loadFirebaseConfig() {

    const response = await fetch(
        "/api/firebase-config",
        {
            method: "GET",
            headers: {
                "Accept": "application/json"
            },
            credentials: "same-origin",
            cache: "no-store"
        }
    );


    if (!response.ok) {

        throw new Error(
            "Unable to load Firebase configuration."
        );
    }


    return await response.json();
}


/* ============================================================
   FIREBASE INITIALIZATION
============================================================ */

let firebaseConfig;

try {

    firebaseConfig =
        await loadFirebaseConfig();

} catch (error) {

    console.error(
        "Firebase configuration error:",
        error
    );

    const errorBox =
        document.getElementById(
            "loginError"
        );

    if (errorBox) {

        errorBox.textContent =
            error.message;

        errorBox.classList.remove(
            "d-none"
        );
    }

    throw error;
}


const firebaseApp =
    initializeApp(
        firebaseConfig
    );


const auth =
    getAuth(
        firebaseApp
    );


/* ============================================================
   DOM
============================================================ */

const form =
    document.getElementById(
        "loginForm"
    );


const errorBox =
    document.getElementById(
        "loginError"
    );


const loginButton =
    document.getElementById(
        "loginBtn"
    );


const emailInput =
    document.getElementById(
        "email"
    );


const passwordInput =
    document.getElementById(
        "password"
    );


const togglePassword =
    document.getElementById(
        "togglePassword"
    );


/* ============================================================
   ERROR
============================================================ */

function showError(message) {

    if (!errorBox) {
        return;
    }


    errorBox.textContent =
        message;


    errorBox.classList.remove(
        "d-none"
    );
}


function hideError() {

    if (!errorBox) {
        return;
    }


    errorBox.textContent =
        "";


    errorBox.classList.add(
        "d-none"
    );
}


/* ============================================================
   PASSWORD TOGGLE
============================================================ */

if (togglePassword) {

    togglePassword.addEventListener(
        "click",
        () => {

            passwordInput.type =
                passwordInput.type ===
                "password"
                    ? "text"
                    : "password";

        }
    );
}


/* ============================================================
   LOGIN
============================================================ */

if (form) {

    form.addEventListener(
        "submit",
        async event => {

            event.preventDefault();

            hideError();


            loginButton.disabled =
                true;


            loginButton.textContent =
                "Signing in...";


            try {

                const email =
                    emailInput.value
                        .trim()
                        .toLowerCase();


                const password =
                    passwordInput.value;


                if (!email) {

                    throw new Error(
                        "Please enter your email address."
                    );
                }


                if (!password) {

                    throw new Error(
                        "Please enter your password."
                    );
                }


                /* --------------------------------------------
                   FIREBASE LOGIN
                -------------------------------------------- */

                const credential =
                    await signInWithEmailAndPassword(
                        auth,
                        email,
                        password
                    );


                console.log(
                    "Firebase authentication successful."
                );


                /* --------------------------------------------
                   FRESH ID TOKEN
                -------------------------------------------- */

                const idToken =
                    await credential.user.getIdToken(
                        true
                    );


                if (!idToken) {

                    throw new Error(
                        "Firebase ID token could not be generated."
                    );
                }


                /* --------------------------------------------
                   CSRF
                -------------------------------------------- */

                const csrfToken =
                    window.CSRF_TOKEN;


                if (!csrfToken) {

                    throw new Error(
                        "Security token is missing. Refresh the page."
                    );
                }


                /* --------------------------------------------
                   CREATE FLASK SESSION
                -------------------------------------------- */

                const response =
                    await fetch(
                        "/api/session",
                        {
                            method: "POST",

                            credentials:
                                "same-origin",

                            cache:
                                "no-store",

                            headers: {

                                "Content-Type":
                                    "application/json",

                                "Accept":
                                    "application/json",

                                "X-CSRFToken":
                                    csrfToken

                            },

                            body:
                                JSON.stringify({

                                    id_token:
                                        idToken

                                })

                        }
                    );


                /* --------------------------------------------
                   RESPONSE
                -------------------------------------------- */

                const contentType =
                    response.headers.get(
                        "content-type"
                    ) || "";


                let data;


                if (
                    contentType.includes(
                        "application/json"
                    )
                ) {

                    data =
                        await response.json();

                } else {

                    const text =
                        await response.text();

                    console.error(
                        "Unexpected Flask response:",
                        text
                    );

                    throw new Error(
                        "The server returned an unexpected response. Check the Flask terminal."
                    );
                }


                /* --------------------------------------------
                   FAILED FLASK SESSION
                -------------------------------------------- */

                if (
                    !response.ok ||
                    !data.success
                ) {

                    /*
                     * Clear Firebase's local login if Flask
                     * refuses to create the application session.
                     */

                    try {

                        await signOut(
                            auth
                        );

                    } catch (logoutError) {

                        console.warn(
                            "Firebase sign-out cleanup failed:",
                            logoutError
                        );
                    }


                    throw new Error(
                        data.message ||
                        "Authentication failed."
                    );
                }


                /* --------------------------------------------
                   SUCCESS
                -------------------------------------------- */

                console.log(
                    "Application session created:",
                    data.user
                );


                window.location.href =
                    data.redirect;


            } catch (error) {

                console.error(
                    "Login error:",
                    error
                );


                let message =
                    error.message ||
                    "Unable to sign in.";


                /* Firebase errors */

                if (
                    message.includes(
                        "auth/invalid-credential"
                    ) ||
                    message.includes(
                        "auth/invalid-login-credentials"
                    )
                ) {

                    message =
                        "Invalid email or password.";

                }

                else if (
                    message.includes(
                        "auth/user-not-found"
                    )
                ) {

                    message =
                        "No Firebase account exists with this email.";

                }

                else if (
                    message.includes(
                        "auth/wrong-password"
                    )
                ) {

                    message =
                        "Incorrect password.";

                }

                else if (
                    message.includes(
                        "auth/too-many-requests"
                    )
                ) {

                    message =
                        "Too many login attempts. Try again later.";

                }

                else if (
                    message.includes(
                        "auth/network-request-failed"
                    )
                ) {

                    message =
                        "Network error. Check your internet connection.";

                }


                showError(
                    message
                );


            } finally {

                loginButton.disabled =
                    false;

                loginButton.textContent =
                    "Sign In";

            }

        }
    );
}