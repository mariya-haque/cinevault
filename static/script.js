
let token = localStorage.getItem("token");

// ==============================
// Signup
// ==============================

async function signup(){

    const username=document.getElementById("signup_username").value;
    const email=document.getElementById("signup_email").value;
    const password=document.getElementById("signup_password").value;

    const response=await fetch("/signup",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify({
            username,
            email,
            password
        })

    });

    const data=await response.json();

    if(response.ok){

        alert("Signup Successful");

        window.location.href="/login";

    }else{

        alert(data.detail);

    }

}

// ==============================
// Login (redirects based on role)
// ==============================

async function login() {

    const username = document.getElementById("login_username").value.trim();
    const password = document.getElementById("login_password").value;

    if (!username || !password) {
        alert("Please fill all fields.");
        return;
    }

    const response = await fetch("/login", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify({
            username,
            password
        })

    });

    const data = await response.json();

    if(response.ok){

        localStorage.setItem("token", data.token);
        localStorage.setItem("username", data.username);
        localStorage.setItem("role", data.role);

        if (data.role === "admin") {
            window.location.href = "/admin/dashboard";
        } else {
            window.location.href = "/dashboard";
        }

    } else {

        alert(data.detail);

    }

}

// ==============================
// Profile
// ==============================

async function profile() {

    token = localStorage.getItem("token");

    const response = await fetch("/profile", {

        method: "GET",

        headers: {
            Authorization: "Bearer " + token
        }

    });

    const data = await response.json();

    if (response.ok) {

        alert(
            "Username : " + data.username +
            "\nEmail : " + data.email +
            "\nRole : " + data.role
        );

    } else {

        alert(data.detail);

    }

}

// ==============================
// Send/Load Chat History
// ==============================

function escapeHtml(str) {
    const div = document.createElement("div");
    div.innerText = str;
    return div.innerHTML;
}

async function loadChatHistory() {

    token = localStorage.getItem("token");
    if (!token) return;

    const chatBox = document.getElementById("chat-box");
    if (!chatBox) return;

    chatBox.innerHTML = `<div class="empty-state">Loading chat history...</div>`;

    const response = await fetch("/chat/history", {
        headers: {
            "Authorization": "Bearer " + token
        }
    });

    if (response.ok) {

        const messages = await response.json();

        if (messages.length === 0) {
            chatBox.innerHTML = `<div class="empty-state">No past messages. Start chatting below!</div>`;
            return;
        }

        chatBox.innerHTML = messages.map((m) => {
            if (m.role === "user") {
                return `
                    <div class="user-message">
                        <b>You:</b><br>${escapeHtml(m.content)}
                    </div>
                `;
            } else {
                return `
                    <div class="bot-message">
                        <b>AI:</b><br>${escapeHtml(m.content)}
                    </div>
                `;
            }
        }).join("");

        chatBox.scrollTop = chatBox.scrollHeight;

    } else {

        chatBox.innerHTML = `<div class="empty-state">Error loading chat history.</div>`;

    }
}

async function sendMessage() {

    token = localStorage.getItem("token");

    const message = document.getElementById("message").value.trim();

    if (message === "") return;

    const chatBox = document.getElementById("chat-box");

    chatBox.innerHTML += `
        <div class="user-message">
            <b>You:</b><br>${escapeHtml(message)}
        </div>
    `;

    document.getElementById("message").value = "";

    const response = await fetch("/chat", {

        method: "POST",

        headers: {

            "Content-Type": "application/json",
            "Authorization": "Bearer " + token

        },

        body: JSON.stringify({

            message: message

        })

    });

    const data = await response.json();

    if (response.ok) {

        chatBox.innerHTML += `
            <div class="bot-message">
                <b>AI:</b><br>${escapeHtml(data.response)}
            </div>
        `;

    } else {

        chatBox.innerHTML += `
            <div class="bot-message">
                Error : ${escapeHtml(data.detail || "Something went wrong")}
            </div>
        `;

    }

    chatBox.scrollTop = chatBox.scrollHeight;

}

// ==============================
// Logout
// ==============================

async function logout() {

    token = localStorage.getItem("token");

    await fetch("/logout", {

        method: "POST",

        headers: {

            Authorization: "Bearer " + token

        }

    });

    localStorage.removeItem("token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");

    window.location.href = "/login";

}

// ==============================
// Delete Account
// ==============================

async function deleteAccount() {

    token = localStorage.getItem("token");

    const confirmDelete = confirm("Are you sure you want to delete your account?");

    if (!confirmDelete) return;

    const response = await fetch("/delete", {

        method: "DELETE",

        headers: {

            Authorization: "Bearer " + token

        }

    });

    const data = await response.json();

    alert(data.message);

    localStorage.removeItem("token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");

    window.location.href = "/signup";

}

// ==============================
// Enter Key Support
// ==============================

document.addEventListener("DOMContentLoaded", () => {

    const messageInput = document.getElementById("message");

    if (messageInput) {

        messageInput.addEventListener("keypress", function (event) {

            if (event.key === "Enter") {

                sendMessage();

            }

        });

    }

});
