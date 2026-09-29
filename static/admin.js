const token = localStorage.getItem("token");
const role = localStorage.getItem("role");

// Guard: must be a logged-in admin
if (!token || role !== "admin") {
    window.location.href = "/login";
}

let editingId = null;
let activeChatUser = null;
let currentMovies = [];

// ==============================
// Section switching (Library / Chats / Comments)
// ==============================

function switchSection(section) {

    ["library", "chats", "comments"].forEach((s) => {
        document.getElementById(`section-${s}`).style.display = (s === section) ? "block" : "none";
        document.getElementById(`nav-${s}`).classList.toggle("active", s === section);
    });

    if (section === "chats") loadChatUsers();
    if (section === "comments") loadComments();
}

// ==============================
// Load movie list
// ==============================

async function loadMovies() {

    const grid = document.getElementById("movie-grid");

    const response = await fetch("/admin/movies", {
        headers: { Authorization: "Bearer " + token }
    });

    if (response.status === 401 || response.status === 403) {
        localStorage.clear();
        window.location.href = "/login";
        return;
    }

    const movies = await response.json();
    currentMovies = movies;

    document.getElementById("movie-count").innerText =
        `${movies.length} title${movies.length === 1 ? "" : "s"} in the library`;

    if (movies.length === 0) {
        grid.innerHTML = `<div class="empty-state">No movies uploaded yet. Add your first title above.</div>`;
        return;
    }

    grid.innerHTML = movies.map(movieCard).join("");
}

function movieCard(m) {

    const date = new Date(m.uploaded_at).toLocaleDateString();

    return `
        <div class="ticket">
            <div class="ticket-stub"><span>ADMIN</span></div>
            <div class="ticket-body">
                <h3>${escapeHtml(m.title)}</h3>
                ${m.genre ? `<span class="ticket-genre">${escapeHtml(m.genre)}</span>` : ""}
                <p class="ticket-desc">${escapeHtml(m.description || "No description provided.")}</p>
                <p class="ticket-meta">File: ${escapeHtml(m.original_filename)} — Added ${date}</p>
                <div class="ticket-actions">
                    <button class="btn btn-ghost" onclick="openEdit('${m.id}')">Edit</button>
                    <button class="btn btn-danger" onclick="deleteMovie('${m.id}')">Delete</button>
                </div>
            </div>
        </div>
    `;
}

// ==============================
// Upload
// ==============================

async function uploadMovie() {

    const title = document.getElementById("up-title").value.trim();
    const genre = document.getElementById("up-genre").value.trim();
    const description = document.getElementById("up-desc").value.trim();
    const fileInput = document.getElementById("up-file");

    if (!title || fileInput.files.length === 0) {
        alert("Title aur file dono zaroori hain.");
        return;
    }

    const formData = new FormData();
    formData.append("title", title);
    formData.append("genre", genre);
    formData.append("description", description);
    formData.append("file", fileInput.files[0]);

    const response = await fetch("/admin/movies", {
        method: "POST",
        headers: { Authorization: "Bearer " + token },
        body: formData
    });

    const data = await response.json();

    if (response.ok) {

        document.getElementById("up-title").value = "";
        document.getElementById("up-genre").value = "";
        document.getElementById("up-desc").value = "";
        fileInput.value = "";

        loadMovies();

    } else {

        alert(data.detail);

    }
}

// ==============================
// Edit
// ==============================

function openEdit(id) {

    const m = currentMovies.find(movie => movie.id === id);
    if (!m) return;

    editingId = id;

    document.getElementById("edit-title").value = m.title;
    document.getElementById("edit-genre").value = m.genre || "";
    document.getElementById("edit-desc").value = m.description || "";

    document.getElementById("edit-modal").classList.add("open");
}

function closeEdit() {
    document.getElementById("edit-modal").classList.remove("open");
    editingId = null;
}

async function saveEdit() {

    if (!editingId) return;

    const title = document.getElementById("edit-title").value.trim();
    const genre = document.getElementById("edit-genre").value.trim();
    const description = document.getElementById("edit-desc").value.trim();

    const response = await fetch(`/admin/movies/${editingId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer " + token
        },
        body: JSON.stringify({ title, genre, description })
    });

    const data = await response.json();

    if (response.ok) {
        closeEdit();
        loadMovies();
    } else {
        alert(data.detail);
    }
}

// ==============================
// Delete
// ==============================

async function deleteMovie(id) {

    const confirmDelete = confirm("Is movie/file ko delete karna hai?");
    if (!confirmDelete) return;

    const response = await fetch(`/admin/movies/${id}`, {
        method: "DELETE",
        headers: { Authorization: "Bearer " + token }
    });

    const data = await response.json();

    if (response.ok) {
        loadMovies();
    } else {
        alert(data.detail);
    }
}

// ==============================
// User Chats (admin viewing)
// ==============================

async function loadChatUsers() {

    const list = document.getElementById("chat-user-list");

    const response = await fetch("/admin/chats", {
        headers: { Authorization: "Bearer " + token }
    });

    if (response.status === 401 || response.status === 403) {
        localStorage.clear();
        window.location.href = "/login";
        return;
    }

    const users = await response.json();

    if (users.length === 0) {
        list.innerHTML = `<div class="empty-state">Koi user ne abhi tak chat nahi ki.</div>`;
        document.getElementById("chat-viewer").style.display = "none";
        return;
    }

    list.innerHTML = users.map((u) => `
        <div class="chat-user-card${u.username === activeChatUser ? " active" : ""}" onclick="loadUserChat('${u.username}')">
            <div class="name">${escapeHtml(u.username)}</div>
            <div class="count">${u.message_count} message${u.message_count === 1 ? "" : "s"}</div>
        </div>
    `).join("");
}

async function loadUserChat(username) {

    activeChatUser = username;

    // Highlight the selected card
    document.querySelectorAll(".chat-user-card").forEach((el) => {
        el.classList.toggle("active", el.querySelector(".name").innerText === username);
    });

    const response = await fetch(`/admin/chats/${username}`, {
        headers: { Authorization: "Bearer " + token }
    });

    const data = await response.json();

    if (!response.ok) {
        alert(data.detail);
        return;
    }

    document.getElementById("chat-viewer").style.display = "block";
    document.getElementById("chat-viewer-title").innerText = `Conversation — ${username}`;

    const chatBox = document.getElementById("chat-box");

    if (data.messages.length === 0) {
        chatBox.innerHTML = `<div class="empty-state">Is user ki koi message history nahi hai.</div>`;
        return;
    }

    chatBox.innerHTML = data.messages.map((m) => {
        if (m.role === "user") {
            return `<div class="user-message"><b>${escapeHtml(username)}:</b><br>${escapeHtml(m.content)}</div>`;
        }
        return `<div class="bot-message"><b>AI:</b><br>${escapeHtml(m.content)}</div>`;
    }).join("");
}

// ==============================
// Comments Moderation
// ==============================

async function loadComments() {

    const container = document.getElementById("comments-list");

    const response = await fetch("/admin/comments", {
        headers: { Authorization: "Bearer " + token }
    });

    if (response.status === 401 || response.status === 403) {
        localStorage.clear();
        window.location.href = "/login";
        return;
    }

    const comments = await response.json();

    if (comments.length === 0) {
        container.innerHTML = `<div class="empty-state">Abhi tak koi comment nahi hai.</div>`;
        return;
    }

    // Sabse naye comment sabse upar
    comments.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    container.innerHTML = comments.map((c) => `
        <div class="comment-card">
            <div>
                <div class="comment-meta">${escapeHtml(c.username)} on "${escapeHtml(c.movie_title)}"</div>
                <p class="comment-text">${escapeHtml(c.text)}</p>
                <div class="comment-date">${new Date(c.created_at).toLocaleString()}</div>
            </div>
            <button class="btn btn-danger" style="padding:6px 12px; font-size:12px;" onclick="deleteCommentAdmin('${c.id}')">Delete</button>
        </div>
    `).join("");
}

async function deleteCommentAdmin(commentId) {

    const confirmDelete = confirm("Ye comment delete karna hai?");
    if (!confirmDelete) return;

    const response = await fetch(`/comments/${commentId}`, {
        method: "DELETE",
        headers: { Authorization: "Bearer " + token }
    });

    const data = await response.json();

    if (response.ok) {
        loadComments();
    } else {
        alert(data.detail);
    }
}

// ==============================
// Logout
// ==============================

async function logoutAdmin() {

    await fetch("/logout", {
        method: "POST",
        headers: { Authorization: "Bearer " + token }
    });

    localStorage.clear();
    window.location.href = "/login";
}

// ==============================
// Helpers
// ==============================

function escapeHtml(str) {
    const div = document.createElement("div");
    div.innerText = str;
    return div.innerHTML;
}

// Safely embed a movie object as a JSON string inside an inline onclick attribute
function attrEscape(m) {
    const safe = {
        title: m.title,
        genre: m.genre || "",
        description: m.description || ""
    };
    return "'" + JSON.stringify(safe).replace(/'/g, "&#39;") + "'";
}

loadMovies();
