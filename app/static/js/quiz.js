/**
 * quiz.js — Upload page logic
 *
 * Handles:
 *  - Drag-and-drop / file browse
 *  - Form submission via AJAX (POST /quiz/generate)
 *  - Loading state during AI generation
 *  - Redirect to quiz taking page on success
 *  - Error display on failure
 */

"use strict";

// ---------------------------------------------------------------------------
// DOM refs (all present on new_quiz.html only)
// ---------------------------------------------------------------------------
const dropZone    = document.getElementById("dropZone");
const browseBtn   = document.getElementById("browseBtn");
const fileInput   = document.getElementById("fileInput");
const textInput   = document.getElementById("textInput");
const generateBtn = document.getElementById("generateBtn");
const errorBox    = document.getElementById("errorBox");
const uploadCard  = document.getElementById("uploadCard");
const loadingCard = document.getElementById("loadingCard");
const dropLabel   = document.getElementById("dropLabel");

// ---------------------------------------------------------------------------
// File selection helpers
// ---------------------------------------------------------------------------
browseBtn.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("click", (e) => {
  if (e.target !== browseBtn) fileInput.click();
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) {
    dropLabel.textContent = `✓ ${fileInput.files[0].name} selected`;
    clearError();
  }
});

// Drag-and-drop
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    // DataTransfer → file input
    const dt = new DataTransfer();
    dt.items.add(files[0]);
    fileInput.files = dt.files;
    dropLabel.textContent = `✓ ${files[0].name} selected`;
    clearError();
  }
});

// ---------------------------------------------------------------------------
// Generate quiz
// ---------------------------------------------------------------------------
generateBtn.addEventListener("click", generateQuiz);

async function generateQuiz() {
  clearError();

  const formData = new FormData();

  if (fileInput.files.length > 0) {
    formData.append("file", fileInput.files[0]);
  } else {
    const text = textInput.value.trim();
    if (!text) {
      showError("Please upload a file or paste your study notes.");
      return;
    }
    if (text.length < 50) {
      showError("Please provide at least 50 characters of text.");
      return;
    }
    formData.append("text", text);
  }

  // Show loading UI
  uploadCard.style.display = "none";
  loadingCard.style.display = "block";
  generateBtn.disabled = true;

  try {
    const response = await fetch("/quiz/generate", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Failed to generate quiz. Please try again.");
    }

    // Redirect to the quiz taking page
    window.location.href = `/quiz/${data.quiz_id}/take`;

  } catch (err) {
    // Restore upload UI and show the error
    loadingCard.style.display = "none";
    uploadCard.style.display = "block";
    generateBtn.disabled = false;
    showError(err.message || "An unexpected error occurred.");
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function showError(msg) {
  errorBox.textContent = msg;
  errorBox.style.display = "block";
  errorBox.scrollIntoView({ behavior: "smooth", block: "center" });
}

function clearError() {
  errorBox.textContent = "";
  errorBox.style.display = "none";
}
