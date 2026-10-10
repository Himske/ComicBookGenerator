const form = document.querySelector("#comic-form");
const button = document.querySelector("#submit-button");
const buttonLabel = document.querySelector("#button-label");
const status = document.querySelector("#status");
const result = document.querySelector("#result");
const comic = document.querySelector("#comic");

function addText(parent, tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  parent.append(element);
  return element;
}

async function readApiResponse(response, failureMessage) {
  const requestId = response.headers.get("x-request-id");
  const requestReference = requestId ? ` (Request ID: ${requestId})` : "";
  const responseText = await response.text();
  let body;
  try {
    body = JSON.parse(responseText);
  } catch {
    const detail = responseText.trim().slice(0, 300);
    if (!response.ok) {
      throw new Error(
        `${detail || `${failureMessage} (HTTP ${response.status}).`}${requestReference}`,
      );
    }
    throw new Error(
      detail
        ? `The server returned an invalid response: ${detail}${requestReference}`
        : `The server returned an empty response (HTTP ${response.status}).${requestReference}`,
    );
  }

  if (!body || typeof body !== "object") {
    throw new Error(
      response.ok
        ? `The server returned an invalid response (HTTP ${response.status}).${requestReference}`
        : `${failureMessage} (HTTP ${response.status}).${requestReference}`,
    );
  }

  if (!response.ok) {
    const rawDetail = body.detail;
    const detail = typeof rawDetail === "string"
      ? rawDetail
      : Array.isArray(rawDetail)
        ? rawDetail
          .map((item) => typeof item?.msg === "string" ? item.msg : JSON.stringify(item))
          .join("; ")
        : rawDetail == null
          ? ""
          : JSON.stringify(rawDetail);
    if (response.status === 405) {
      const path = new URL(response.url).pathname;
      throw new Error(
        `${detail || "The server does not allow this request method."} ` +
        `(HTTP 405 at ${path})${requestReference}.`,
      );
    }
    if (detail) {
      throw new Error(`${detail}${requestReference}`);
    }
    throw new Error(`${failureMessage} (HTTP ${response.status}).${requestReference}`);
  }
  return body;
}

function showComic(response) {
  comic.replaceChildren();
  comic.hidden = false;

  const heading = document.createElement("header");
  heading.className = "comic-heading";
  addText(heading, "h2", "Your comic");
  addText(heading, "p", `Style: ${response.style} · ID: ${response.comic_id}`, "comic-meta");
  comic.append(heading);

  const panels = document.createElement("div");
  panels.className = "panels";
  for (const panel of response.panels) {
    const card = document.createElement("article");
    card.className = "comic-card";
    addText(card, "h3", `Panel ${panel.number}`);
    addText(card, "p", panel.description);
    if (panel.dialogue) {
      const dialogue = document.createElement("p");
      addText(dialogue, "strong", "Dialogue: ");
      dialogue.append(document.createTextNode(panel.dialogue));
      card.append(dialogue);
    }
    const prompt = document.createElement("p");
    addText(prompt, "strong", "Image prompt: ");
    prompt.append(document.createTextNode(panel.image_prompt));
    card.append(prompt);
    panels.append(card);
  }
  comic.append(panels);
}

if (form) form.addEventListener("submit", async (event) => {
  event.preventDefault();
  status.className = "";
  status.textContent = "Creating your comic… This may take a little while.";
  comic.replaceChildren();
  comic.hidden = true;
  button.disabled = true;
  buttonLabel.textContent = "Generating…";
  result.setAttribute("aria-busy", "true");

  const formData = new FormData(form);
  const request = {
    premise: formData.get("premise"),
    panel_count: Number(formData.get("panel_count")),
    style: formData.get("style"),
  };

  try {
    const response = await fetch("/comics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    const body = await readApiResponse(
      response,
      "The comic could not be generated. Please try again.",
    );
    status.textContent = "";
    showComic(body);
  } catch (error) {
    status.className = "error";
    status.textContent = error instanceof Error
      ? error.message
      : "Something went wrong while generating your comic.";
  } finally {
    button.disabled = false;
    buttonLabel.textContent = "Generate my comic";
    result.setAttribute("aria-busy", "false");
  }
});

const characterForm = document.querySelector("#character-form");
const characterExamplesForm = document.querySelector("#character-examples-form");
const characterButton = document.querySelector("#character-submit-button");
const characterButtonLabel = document.querySelector("#character-button-label");
const examplesButton = document.querySelector("#examples-submit-button");
const examplesButtonLabel = document.querySelector("#examples-button-label");
const characterStatus = document.querySelector("#character-status");
const characterResult = document.querySelector("#character-result");
const characterPromptCard = document.querySelector("#character-prompt-card");
const characterPromptOutput = document.querySelector("#character-prompt-output");

async function submitCharacterPrompt(event, form, button, buttonLabel, useImages) {
  event.preventDefault();
  characterStatus.className = "";
  characterPromptCard.hidden = true;
  characterStatus.textContent = "Creating your character prompt…";
  button.disabled = true;
  buttonLabel.textContent = "Generating…";
  characterResult.setAttribute("aria-busy", "true");

  try {
    let response;
    if (useImages) {
      const request = new FormData(form);
      response = await fetch("/character-prompt/from-examples", {
        method: "POST",
        body: request,
      });
    } else {
      const request = Object.fromEntries(new FormData(form).entries());
      response = await fetch("/character-prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
    }

    const body = await readApiResponse(
      response,
      "The character prompt could not be generated. Please try again.",
    );
    characterStatus.textContent = "";
    characterPromptOutput.textContent = body.prompt;
    characterPromptCard.hidden = false;
  } catch (error) {
    characterStatus.className = "error";
    characterStatus.textContent = error instanceof Error
      ? error.message
      : "Something went wrong while generating the character prompt.";
  } finally {
    button.disabled = false;
    buttonLabel.textContent = useImages ? "Generate from images" : "Generate from traits";
    characterResult.setAttribute("aria-busy", "false");
  }
}

if (characterForm) characterForm.addEventListener("submit", (event) => {
  submitCharacterPrompt(
    event,
    characterForm,
    characterButton,
    characterButtonLabel,
    false,
  );
});

if (characterExamplesForm) characterExamplesForm.addEventListener("submit", (event) => {
  submitCharacterPrompt(
    event,
    characterExamplesForm,
    examplesButton,
    examplesButtonLabel,
    true,
  );
});
