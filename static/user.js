const token = localStorage.getItem("token");
const role = localStorage.getItem("role");

// Guard: must be logged in
if (!token) {
    window.location.href = "/login";
}

// Admins get redirected to their own dashboard
if (role === "admin") {
    window.location.href = "/admin/dashboard";
}

let currentMovieId = null;

// ==============================
// Load movie list
// ==============================

async function loadMovies() {

    const grid = document.getElementById("movie-grid");

    const response = await fetch("/movies", {
        headers: { Authorization: "Bearer " + token }
    });

    if (response.status === 401) {
        localStorage.clear();
        window.location.href = "/login";
        return;
    }

    const movies = await response.json();

    if (movies.length === 0) {
        grid.innerHTML = `<div class="empty-state">No movies available yet. Check back soon.</div>`;
        return;
    }

    grid.innerHTML = movies.map(movieCard).join("");
}

function movieCard(m) {

    const date = new Date(m.uploaded_at).toLocaleDateString();

    return `
        <div class="ticket">
            <div class="ticket-stub"><span>CINEVAULT</span></div>
            <div class="ticket-body">
                <h3>${escapeHtml(m.title)}</h3>
                ${m.genre ? `<span class="ticket-genre">${escapeHtml(m.genre)}</span>` : ""}
                <p class="ticket-desc">${escapeHtml(m.description || "No description provided.")}</p>
                <p class="ticket-meta">Added ${date}</p>
                <div class="ticket-actions">
                    <button class="btn btn-ghost" onclick="openDetails('${m.id}')">Details</button>
                    <button class="btn btn-primary" style="width:auto;" onclick="downloadMovie('${m.id}')">Download</button>
                </div>
            </div>
        </div>
    `;
}

// ==============================
// Details modal
// ==============================

async function openDetails(id) {

    const response = await fetch(`/movies/${id}`, {
        headers: { Authorization: "Bearer " + token }
    });

    const data = await response.json();

    if (!response.ok) {
        alert(data.detail);
        return;
    }

    currentMovieId = id;

    document.getElementById("details-title").innerText = data.title;
    document.getElementById("details-genre").innerText = data.genre || "Uncategorized";
    document.getElementById("details-desc").innerText = data.description || "No description provided.";
    document.getElementById("details-meta").innerText =
        `File: ${data.original_filename} — Added ${new Date(data.uploaded_at).toLocaleDateString()}`;

    document.getElementById("details-download").onclick = () => downloadMovie(id);

    document.getElementById("details-modal").classList.add("open");

    loadComments(id);
}

function closeDetails() {
    document.getElementById("details-modal").classList.remove("open");
}

// ==============================
// Comments
// ==============================

async function loadComments(movieId) {

    const container = document.getElementById("comments-list");
    container.innerHTML = `<div class="empty-state">Loading comments...</div>`;

    const response = await fetch(`/movies/${movieId}/comments`, {
        headers: { Authorization: "Bearer " + token }
    });

    const comments = await response.json();

    if (!response.ok) {
        container.innerHTML = `<div class="empty-state">Comments load nahi ho sake.</div>`;
        return;
    }

    if (comments.length === 0) {
        container.innerHTML = `<div class="empty-state">Abhi tak koi comment nahi hai. Pehla comment aap likhein!</div>`;
        return;
    }

    const myUsername = localStorage.getItem("username");

    container.innerHTML = comments.map((c) => `
        <div class="comment-item">
            <div class="comment-item-top">
                <span class="comment-author">${escapeHtml(c.username)}</span>
                ${c.username === myUsername ? `<button class="link-btn" onclick="deleteOwnComment('${c.id}', '${movieId}')">Delete</button>` : ""}
            </div>
            <div class="comment-item-text">${escapeHtml(c.text)}</div>
        </div>
    `).join("");
}

async function postComment() {

    const input = document.getElementById("comment-input");
    const text = input.value.trim();

    if (!text || !currentMovieId) return;

    const response = await fetch(`/movies/${currentMovieId}/comments`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer " + token
        },
        body: JSON.stringify({ text })
    });

    const data = await response.json();

    if (response.ok) {
        input.value = "";
        loadComments(currentMovieId);
    } else {
        alert(data.detail);
    }
}

async function deleteOwnComment(commentId, movieId) {

    const confirmDelete = confirm("Apna comment delete karna hai?");
    if (!confirmDelete) return;

    const response = await fetch(`/comments/${commentId}`, {
        method: "DELETE",
        headers: { Authorization: "Bearer " + token }
    });

    const data = await response.json();

    if (response.ok) {
        loadComments(movieId);
    } else {
        alert(data.detail);
    }
}

// ==============================
// Download
// ==============================

// Download uses Authorization header via fetch + blob,
// since a plain link/window.open can't send custom headers.
async function downloadMovie(id) {

    const response = await fetch(`/movies/${id}/download`, {
        headers: { Authorization: "Bearer " + token }
    });

    if (!response.ok) {
        const data = await response.json();
        alert(data.detail || "Download failed");
        return;
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : "download";

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
}

// ==============================
// Profile / Logout / Delete
// ==============================

async function viewProfile() {

    const response = await fetch("/profile", {
        headers: { Authorization: "Bearer " + token }
    });

    const data = await response.json();

    if (response.ok) {
        alert(`Username : ${data.username}\nEmail : ${data.email}\nRole : ${data.role}`);
    } else {
        alert(data.detail);
    }
}

async function logoutUser() {

    await fetch("/logout", {
        method: "POST",
        headers: { Authorization: "Bearer " + token }
    });

    localStorage.clear();
    window.location.href = "/login";
}

async function deleteAccountUser() {

    const confirmDelete = confirm("Are you sure you want to delete your account?");
    if (!confirmDelete) return;

    const response = await fetch("/delete", {
        method: "DELETE",
        headers: { Authorization: "Bearer " + token }
    });

    const data = await response.json();
    alert(data.message);

    localStorage.clear();
    window.location.href = "/signup";
}

// ==============================
// Helpers
// ==============================

function escapeHtml(str) {
    const div = document.createElement("div");
    div.innerText = str;
    return div.innerHTML;
}

loadMovies();
