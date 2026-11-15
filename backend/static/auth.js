// ==========================================
// ZORIN AUTHENTICATION SYSTEM
// Login, Registration & Session Management
// ==========================================

(() => {
    const TOKEN_KEY = "zorin_auth_token";
    const USER_KEY = "zorin_user";

    const originalFetch = window.fetch.bind(window);

    let authOverlay;
    let isCheckingSession = false;

    // ------------------------------------------
    // TOKEN MANAGEMENT
    // ------------------------------------------

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function saveSession(token, user) {
        localStorage.setItem(TOKEN_KEY, token);
        localStorage.setItem(USER_KEY, JSON.stringify(user));
    }

    function clearSession() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    }

    // ------------------------------------------
    // AUTOMATIC AUTHORIZATION HEADER
    // ------------------------------------------

    window.fetch = async function (input, init = {}) {
        const requestUrl = input instanceof Request
            ? input.url
            : String(input);

        const headers = new Headers(
            init.headers ||
            (input instanceof Request ? input.headers : undefined)
        );

        const token = getToken();

        if (token && requestUrl.includes("/api/")) {
            headers.set("Authorization", `Bearer ${token}`);
        }

        const response = await originalFetch(input, {
            ...init,
            headers
        });

        const isAuthEndpoint =
            requestUrl.includes("/api/auth/login") ||
            requestUrl.includes("/api/auth/register") ||
            requestUrl.includes("/api/auth/me");

        if (response.status === 401 && !isAuthEndpoint && token) {
            clearSession();
            showAuthScreen();
        }

        return response;
    };

    // ------------------------------------------
    // AUTHENTICATION SCREEN
    // ------------------------------------------

    function createAuthScreen() {
        if (document.getElementById("zorinAuthOverlay")) return;

        authOverlay = document.createElement("div");
        authOverlay.id = "zorinAuthOverlay";

        authOverlay.innerHTML = `
            <div class="zorin-auth-card">

                <div class="zorin-auth-logo">✦ ZORIN</div>

                <h1 id="authHeading">Welcome Back</h1>

                <p id="authSubtitle">
                    Your personal AI assistant is waiting.
                </p>

                <form id="zorinAuthForm">

                    <div id="authNameField" class="auth-field" hidden>
                        <label>Display Name</label>
                        <input
                            type="text"
                            id="authName"
                            placeholder="Your name"
                            autocomplete="name"
                        >
                    </div>

                    <div class="auth-field">
                        <label>Email Address</label>
                        <input
                            type="email"
                            id="authEmail"
                            placeholder="Enter your email"
                            autocomplete="email"
                            required
                        >
                    </div>

                    <div class="auth-field">
                        <label>Password</label>
                        <input
                            type="password"
                            id="authPassword"
                            placeholder="Enter your password"
                            autocomplete="current-password"
                            required
                            minlength="6"
                        >
                    </div>

                    <div id="authError" role="alert"></div>

                    <button type="submit" id="authSubmit">
                        Login to ZORIN
                    </button>

                </form>

                <p class="auth-switch">
                    <span id="authSwitchText">Don't have an account?</span>
                    <button type="button" id="authSwitchButton">
                        Create Account
                    </button>
                </p>

                <div class="auth-footer">
                    Powered by ZORIN AI
                </div>

            </div>
        `;

        document.body.appendChild(authOverlay);

        document.getElementById("zorinAuthForm")
            .addEventListener("submit", handleAuthSubmit);

        document.getElementById("authSwitchButton")
            .addEventListener("click", toggleAuthMode);
    }

    // ------------------------------------------
    // LOGIN / REGISTER MODE
    // ------------------------------------------

    let isRegisterMode = false;

    function toggleAuthMode() {
        isRegisterMode = !isRegisterMode;

        document.getElementById("authHeading").textContent =
            isRegisterMode ? "Create Your Account" : "Welcome Back";

        document.getElementById("authSubtitle").textContent =
            isRegisterMode
                ? "Create your personal ZORIN account."
                : "Your personal AI assistant is waiting.";

        document.getElementById("authNameField").hidden =
            !isRegisterMode;

        document.getElementById("authPassword").autocomplete =
            isRegisterMode ? "new-password" : "current-password";

        document.getElementById("authSubmit").textContent =
            isRegisterMode ? "Create Account" : "Login to ZORIN";

        document.getElementById("authSwitchText").textContent =
            isRegisterMode
                ? "Already have an account?"
                : "Don't have an account?";

        document.getElementById("authSwitchButton").textContent =
            isRegisterMode ? "Login" : "Create Account";

        document.getElementById("authError").textContent = "";
    }

    // ------------------------------------------
    // LOGIN / REGISTER SUBMISSION
    // ------------------------------------------

    async function handleAuthSubmit(event) {
        event.preventDefault();

        const email = document.getElementById("authEmail")
            .value.trim();

        const password = document.getElementById("authPassword")
            .value;

        const displayName = document.getElementById("authName")
            .value.trim();

        const errorBox = document.getElementById("authError");
        const submitButton = document.getElementById("authSubmit");

        errorBox.textContent = "";
        submitButton.disabled = true;
        submitButton.textContent = "Please wait...";

        try {
            const endpoint = isRegisterMode
                ? "/api/auth/register"
                : "/api/auth/login";

            const payload = isRegisterMode
                ? {
                    email,
                    password,
                    display_name: displayName,
                    voice_preference: "Aoede"
                }
                : {
                    email,
                    password
                };

            const response = await originalFetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Authentication failed."
                );
            }

            if (!data.token || !data.user) {
                throw new Error("Invalid server response.");
            }

            saveSession(data.token, data.user);

            hideAuthScreen();

            window.location.reload();

        } catch (error) {
            errorBox.textContent = error.message;
        } finally {
            submitButton.disabled = false;
            submitButton.textContent =
                isRegisterMode ? "Create Account" : "Login to ZORIN";
        }
    }

    // ------------------------------------------
    // SHOW / HIDE AUTH SCREEN
    // ------------------------------------------

    function showAuthScreen() {
        if (!authOverlay) createAuthScreen();

        authOverlay.style.display = "flex";
    }

    function hideAuthScreen() {
        if (authOverlay) {
            authOverlay.style.display = "none";
        }
    }

    // ------------------------------------------
    // SESSION VALIDATION
    // ------------------------------------------

    async function checkExistingSession() {
        const token = getToken();

        if (!token) {
            showAuthScreen();
            return;
        }

        isCheckingSession = true;

        try {
            const response = await originalFetch("/api/auth/me", {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            if (!response.ok) {
                clearSession();
                showAuthScreen();
                return;
            }

            const data = await response.json();

            if (!data.success || !data.user) {
                clearSession();
                showAuthScreen();
                return;
            }

            localStorage.setItem(
                USER_KEY,
                JSON.stringify(data.user)
            );

            hideAuthScreen();

        } catch (error) {
            console.error("Session validation error:", error);
            showAuthScreen();
        } finally {
            isCheckingSession = false;
        }
    }

    // ------------------------------------------
    // INITIALIZATION
    // ------------------------------------------

    document.addEventListener("DOMContentLoaded", () => {
        createAuthScreen();
        checkExistingSession();
    });

    // Allow other scripts to access authentication state.
    window.ZORIN_AUTH = {
        getToken,
        getUser: () => {
            try {
                return JSON.parse(localStorage.getItem(USER_KEY));
            } catch {
                return null;
            }
        },
        logout: () => {
            clearSession();
            showAuthScreen();
        }
    };

})();