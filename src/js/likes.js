// Heart (like) buttons for posts and projects, shared by every page that shows them.
//
// Server-rendered pages put this where the heart goes:
//   <button class="like-button" data-kind="post|project" data-id="..." data-liked="true|false" data-count="3"></button>
// and pages that build cards in JavaScript call likeButton(kind, id, likes) instead.
// Include <script src="/js/likes.js"></script> after the buttons.
(() => {
  const style = document.createElement("style");
  style.textContent = `
    .like-button {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      align-self: flex-start;
      padding: 4px 12px;
      border: none;
      border-radius: 16px;
      background-color: rgba(255, 255, 255, 0.8);
      color: #333;
      font: inherit;
      cursor: pointer;
    }
    .like-button .heart { color: #999; font-size: 1.15em; line-height: 1; }
    .like-button[aria-pressed=true] .heart { color: #e0245e; }
    .like-button:disabled { cursor: default; opacity: 0.7; }
  `;
  document.head.append(style);

  const render = button => {
    const liked = button.dataset.liked === "true";
    const count = Number(button.dataset.count);
    button.type = "button";  // never submits a form
    button.setAttribute("aria-pressed", liked);
    button.title = liked ? "Unlike" : "Like";

    const heart = document.createElement("span");
    heart.className = "heart";
    heart.textContent = liked ? "♥" : "♡";  // filled / outline heart

    const label = document.createElement("span");
    label.textContent = `${count} ${count === 1 ? "like" : "likes"}`;
    button.replaceChildren(heart, label);
  };

  window.likeButton = (kind, id, likes) => {
    const button = document.createElement("button");
    button.className = "like-button";
    Object.assign(button.dataset, { kind, id, liked: likes.liked, count: likes.count });
    render(button);
    return button;
  };

  // One listener for every heart, including ones added later (e.g. the next page of projects)
  document.addEventListener("click", async event => {
    const button = event.target.closest(".like-button");
    if (!button) return;
    // Hearts can sit inside a card that links to the project; liking shouldn't open it
    event.preventDefault();
    event.stopPropagation();
    if (button.disabled) return;

    const like = button.dataset.liked !== "true";
    button.disabled = true;
    const response = await fetch(`/${button.dataset.kind}s/${button.dataset.id}/like`, { method: like ? "POST" : "DELETE" });
    button.disabled = false;
    if (!response.ok) return;

    const result = await response.json();
    button.dataset.liked = result.liked;
    button.dataset.count = result.count;
    render(button);
  });

  document.querySelectorAll(".like-button").forEach(render);
})();
