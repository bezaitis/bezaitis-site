// Photo viewer for trip and gallery pages. Each photo is a link to the
// full-size file, so the page still works without this script.
(() => {
  const root = document.querySelector("[data-gallery]");
  const dlg = document.querySelector(".lightbox");
  if (!root || !dlg || typeof dlg.showModal !== "function") return;

  const links = [...root.querySelectorAll(".photo-btn")].sort((a, b) => a.dataset.index - b.dataset.index);
  const img = document.createElement("img");
  dlg.querySelector(".lightbox-stage").append(img);
  const count = dlg.querySelector(".count");
  let current = 0;
  let opener = null;

  const show = (n) => {
    current = (n + links.length) % links.length;
    const link = links[current];
    img.src = link.href;
    img.alt = link.querySelector("img").alt;
    count.textContent = `Photo ${current + 1} of ${links.length}`;
    const next = links[(current + 1) % links.length];
    new Image().src = next.href;
  };

  links.forEach((link, n) =>
    link.addEventListener("click", (e) => {
      e.preventDefault();
      opener = link;
      show(n);
      dlg.showModal();
    })
  );
  dlg.querySelectorAll("[data-step]").forEach((b) => b.addEventListener("click", () => show(current + Number(b.dataset.step))));
  dlg.querySelector("[data-close]").addEventListener("click", () => dlg.close());
  dlg.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") show(current + 1);
    if (e.key === "ArrowLeft") show(current - 1);
  });
  dlg.addEventListener("click", (e) => {
    if (e.target === dlg || e.target.classList.contains("lightbox-stage")) dlg.close();
  });
  dlg.addEventListener("close", () => opener?.focus());
})();
