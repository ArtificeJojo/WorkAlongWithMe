// Technical skills: the picker used on /aboutyou, the project form and the project page, plus the
// read-only bubbles shown on project cards. Any skill can be typed; the suggestions come from skills.txt.
(() => {
  const MAX_SHOWN = 8;
  let pickers = 0;

  const style = document.createElement("style");
  style.textContent = `
    .skill-picker .skill-list { display: flex; flex-wrap: wrap; gap: 8px; list-style: none; padding: 0; margin: 0 0 8px; clear: both; }
    .skill-picker .skill-list li { display: flex; align-items: center; gap: 4px; padding: 2px 4px 2px 10px; border-radius: 16px; background-color: rgb(107, 204, 236); color: #222; }
    .skill-picker .skill-list button { border: none; background: none; cursor: pointer; font-size: 1em; line-height: 1; padding: 2px 6px; }
    .skill-picker .skill-entry { position: relative; display: flex; gap: 8px; }
    .skill-picker .skill-entry input { flex: 1; padding: 4px 8px; border: 1px solid #888; border-radius: 8px; font: inherit; }
    .skill-picker .skill-suggestions { position: absolute; top: 100%; left: 0; right: 0; z-index: 1; list-style: none; margin: 2px 0 0; padding: 4px 0;
      background-color: white; color: #222; border: 1px solid rgb(35, 105, 246); border-radius: 8px; max-height: 240px; overflow-y: auto; }
    .skill-picker .skill-suggestions li { padding: 4px 10px; cursor: pointer; }
    .skill-picker .skill-suggestions li[aria-selected="true"], .skill-picker .skill-suggestions li:hover { background-color: rgb(107, 204, 236); }
    .skill-picker .hint { margin: 6px 0 0; font-size: 0.85em; color: #555; }
    .skill-picker .error { margin: 6px 0 0; color: #b00020; font-weight: bold; }
    .skill-tags { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; list-style: none; padding: 0; margin: 0; }
    .skill-tags li { padding: 2px 8px; border-radius: 16px; background-color: rgb(107, 204, 236); color: #222;
      font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; font-size: 12px; overflow-wrap: anywhere; }
  `;
  document.head.append(style);

  const element = (tag, props = {}) => Object.assign(document.createElement(tag), props);

  // Read-only bubbles, e.g. under a project card's title
  window.skillTags = skills => {
    const list = element("ul", { className: "skill-tags" });
    list.setAttribute("aria-label", "Skills");
    list.append(...skills.map(skill => element("li", { textContent: skill })));
    return list;
  };

  // Builds the picker inside container. Options: suggestions, max, maxLength, initial, name (adds a
  // hidden input per skill so a plain form submits them), exclude (skills already held elsewhere, e.g.
  // on the profile: not suggested and can't be added again). Returns { skills(), commit(), error(text), focus() }.
  window.skillPicker = (container, { suggestions = [], max = 5, maxLength = 50, initial = [], name = null, exclude = [] } = {}) => {
    const id = `skillPicker${++pickers}`;
    const placeholder = "e.g. Python, then press Enter";
    let skills = [];
    let matches = [];
    let active = 0;

    const list = element("ul", { className: "skill-list" });
    const input = element("input", { type: "text", autocomplete: "off", maxLength, placeholder });
    const dropdown = element("ul", { className: "skill-suggestions", id: `${id}Suggestions`, hidden: true });
    const addButton = element("button", { type: "button", textContent: "Add" });
    const hint = element("p", { className: "hint", id: `${id}Hint`, textContent: "Press Tab to complete to the first suggestion, Enter to add." });
    const errorText = element("p", { className: "error", id: `${id}Error`, hidden: true });
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-controls", dropdown.id);
    input.setAttribute("aria-describedby", `${hint.id} ${errorText.id}`);
    dropdown.setAttribute("role", "listbox");
    errorText.setAttribute("role", "alert");
    const entry = element("div", { className: "skill-entry" });
    entry.append(input, dropdown, addButton);
    container.classList.add("skill-picker");
    container.append(list, entry, hint, errorText);

    const isAdded = skill => [...skills, ...exclude].some(s => s.toLowerCase() === skill.toLowerCase());
    const error = text => { errorText.textContent = text; errorText.hidden = !text; };

    const highlight = () => {
      dropdown.querySelectorAll("li").forEach((option, i) => option.setAttribute("aria-selected", String(i === active)));
      if (matches.length) input.setAttribute("aria-activedescendant", `${id}Option${active}`);
      else input.removeAttribute("aria-activedescendant");
    };

    const hideDropdown = () => { dropdown.hidden = true; input.setAttribute("aria-expanded", "false"); };

    // Suggest listed skills that start with what's been typed so far, ignoring case
    const refresh = () => {
      const typed = input.value.trim().toLowerCase();
      matches = typed ? suggestions.filter(s => s.toLowerCase().startsWith(typed) && !isAdded(s)).slice(0, MAX_SHOWN) : [];
      active = 0;
      dropdown.replaceChildren(...matches.map((skill, i) => {
        const option = element("li", { id: `${id}Option${i}`, textContent: skill });
        option.setAttribute("role", "option");
        // mousedown, so the input doesn't lose focus first
        option.onmousedown = event => { event.preventDefault(); add(skill); };
        return option;
      }));
      dropdown.hidden = !matches.length;
      input.setAttribute("aria-expanded", String(matches.length > 0));
      highlight();
    };

    const render = next => {
      skills = next;
      list.replaceChildren(...skills.map(skill => {
        const item = element("li");
        const remove = element("button", { type: "button", textContent: "×" });
        remove.setAttribute("aria-label", `Remove ${skill}`);
        remove.onclick = () => { render(skills.filter(s => s !== skill)); input.focus(); };
        item.append(element("span", { textContent: skill }), remove);
        if (name) item.append(element("input", { type: "hidden", name, value: skill }));
        return item;
      }));
      const full = skills.length >= max;
      input.disabled = full;
      addButton.disabled = full;
      input.placeholder = full ? `That's ${max} skills` : placeholder;
      error("");
      refresh();
    };

    // Typed skills that match a listed one take its spelling, e.g. "python" -> "Python"
    const add = text => {
      const typed = text.replace(/\s+/g, " ").trim();
      if (!typed) return;
      const skill = suggestions.find(s => s.toLowerCase() === typed.toLowerCase()) || typed;
      if (isAdded(skill)) {
        const inPicker = skills.some(s => s.toLowerCase() === skill.toLowerCase());
        error(`${skill} is already ${inPicker ? "on the list" : "one of your skills"}.`);
        return;
      }
      if (skills.length >= max) { error(`You can list up to ${max} skills.`); return; }
      input.value = "";
      render([...skills, skill]);
    };

    input.addEventListener("input", () => { error(""); refresh(); });
    input.addEventListener("blur", hideDropdown);
    input.addEventListener("focus", refresh);
    input.addEventListener("keydown", event => {
      if (event.key === "Tab" && !event.shiftKey && matches.length && input.value !== matches[active]) {
        // Complete to the first suggestion (or the one picked with the arrow keys); a second Tab moves on as usual
        event.preventDefault();
        input.value = matches[active];
        refresh();
      } else if (event.key === "ArrowDown" && matches.length) {
        event.preventDefault();
        active = (active + 1) % matches.length;
        highlight();
      } else if (event.key === "ArrowUp" && matches.length) {
        event.preventDefault();
        active = (active - 1 + matches.length) % matches.length;
        highlight();
      } else if (event.key === "Enter" && input.value.trim()) {
        // Add the skill instead of submitting the form
        event.preventDefault();
        add(input.value);
      } else if (event.key === "Escape") {
        hideDropdown();
      }
    });
    addButton.onclick = () => { add(input.value); input.focus(); };

    render(initial.slice());
    return {
      skills: () => skills.slice(),
      // Anything still in the box counts too, e.g. when the form is submitted
      commit: () => { if (input.value.trim()) add(input.value); return skills.slice(); },
      error,
      focus: () => input.focus(),
    };
  };
})();
