const notesList = document.querySelector("#notes-list");
const emptyState = document.querySelector("#empty-state");
const editorPanel = document.querySelector("#editor-panel");
const newNoteButton = document.querySelector("#new-note-button");
const saveNoteButton = document.querySelector("#save-note-button");
const deleteNoteButton = document.querySelector("#delete-note-button");
const saveStatus = document.querySelector("#save-status");
const titleInput = document.querySelector("#note-title");
const contentInput = document.querySelector("#note-content");

let notes = [];
let selectedNoteId = null;

function selectedNote() {
  return notes.find((note) => note.id === selectedNoteId);
}

function setStatus(message) {
  saveStatus.textContent = message;
}

function showEditor(show) {
  emptyState.classList.toggle("hidden", show);
  editorPanel.classList.toggle("hidden", !show);
  editorPanel.classList.toggle("flex", show);
}

function renderNotes() {
  notesList.innerHTML = "";

  notes.forEach((note) => {
    const button = document.createElement("button");
    const isSelected = note.id === selectedNoteId;

    button.type = "button";
    button.className = [
      "w-full rounded-md px-3 py-2 text-left text-sm hover:bg-zinc-200",
      isSelected ? "bg-zinc-200 font-medium" : "text-zinc-700",
    ].join(" ");
    button.textContent = note.title || "Sem titulo";
    button.addEventListener("click", () => selectNote(note.id));

    notesList.appendChild(button);
  });
}

function renderEditor() {
  const note = selectedNote();

  if (!note) {
    showEditor(false);
    return;
  }

  showEditor(true);
  titleInput.value = note.title || "";
  contentInput.value = note.content || "";
  setStatus("");
}

function selectNote(noteId) {
  selectedNoteId = noteId;
  renderNotes();
  renderEditor();
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Erro inesperado.");
  }

  return data;
}

async function loadNotes() {
  try {
    const response = await fetch("/api/notes");

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Erro no CRUD:", errorData);
      alert("Erro ao listar notas: " + (errorData.detalhes || errorData.error));
      return;
    }

    const data = await response.json();
    notes = data.notes || [];
    selectedNoteId = notes[0]?.id || null;
    renderNotes();
    renderEditor();
  } catch (error) {
    console.error("Erro inesperado no frontend:", error);
    setStatus(error.message);
  }
}

async function createNote() {
  const payload = {
    title: "Nova nota",
    content: "",
  };

  try {
    const response = await fetch("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Erro detalhado do Backend:", errorData);
      alert(
        "Erro ao criar nota: " +
          (errorData.detalhes || errorData.error) +
          (errorData.hint ? "\n\n" + errorData.hint : "")
      );
      return;
    }

    const data = await response.json();
    const createdNote = data.note || data.data?.[0];

    if (createdNote) {
      notes = [createdNote, ...notes];
      selectNote(createdNote.id);
      titleInput.focus();
      titleInput.select();
    }
  } catch (error) {
    console.error("Erro inesperado ao criar nota:", error);
    setStatus(error.message);
  }
}

async function saveNote() {
  if (!selectedNoteId) {
    return;
  }

  setStatus("Salvando...");

  try {
    const response = await fetch(`/api/notes/${selectedNoteId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: titleInput.value,
        content: contentInput.value,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Erro no CRUD:", errorData);
      alert("Erro ao atualizar nota: " + (errorData.detalhes || errorData.error));
      setStatus("Erro ao salvar");
      return;
    }

    const data = await response.json();
    const updatedNote = data.note || data.data?.[0];

    if (updatedNote) {
      notes = notes.map((note) => (note.id === selectedNoteId ? updatedNote : note));
    }

    renderNotes();
    setStatus("Salvo");
  } catch (error) {
    console.error("Erro inesperado no frontend:", error);
    setStatus(error.message);
  }
}

async function deleteNote() {
  if (!selectedNoteId) {
    return;
  }

  const confirmed = window.confirm("Deletar esta nota?");
  if (!confirmed) {
    return;
  }

  try {
    const response = await fetch(`/api/notes/${selectedNoteId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Erro no CRUD:", errorData);
      alert("Erro ao deletar nota: " + (errorData.detalhes || errorData.error));
      return;
    }

    notes = notes.filter((note) => note.id !== selectedNoteId);
    selectedNoteId = notes[0]?.id || null;
    renderNotes();
    renderEditor();
  } catch (error) {
    console.error("Erro inesperado no frontend:", error);
    setStatus(error.message);
  }
}

titleInput.addEventListener("input", () => {
  const note = selectedNote();
  if (note) {
    note.title = titleInput.value;
    renderNotes();
    setStatus("Alteracoes nao salvas");
  }
});

contentInput.addEventListener("input", () => {
  const note = selectedNote();
  if (note) {
    note.content = contentInput.value;
    setStatus("Alteracoes nao salvas");
  }
});

newNoteButton.addEventListener("click", createNote);
saveNoteButton.addEventListener("click", saveNote);
deleteNoteButton.addEventListener("click", deleteNote);

loadNotes();
