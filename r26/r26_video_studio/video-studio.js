(() => {
  "use strict";
  const parts = [
    "video-studio.part01.js.txt","video-studio.part02.js.txt","video-studio.part03.js.txt","video-studio.part04.js.txt",
    "video-studio.part05.js.txt","video-studio.part06.js.txt","video-studio.part07a.js.txt","video-studio.part07b.js.txt",
    "video-studio.part07c.js.txt","video-studio.part08.js.txt"
  ];
  Promise.all(parts.map(async name => {
    const response = await fetch(name, {cache:"no-store"});
    if (!response.ok) throw new Error(`No se pudo cargar ${name}: HTTP ${response.status}`);
    return response.text();
  })).then(rows => {
    const source = rows.join("");
    (0, eval)(`${source}\n//# sourceURL=binario-video-studio-r27-assembled.js`);
  }).catch(error => {
    console.error("Binario Video Studio source hydration failed", error);
    const box = document.createElement("div");
    box.style.cssText = "position:fixed;inset:20px;z-index:99999;padding:18px;background:#32151a;color:white;border:1px solid #7c333f;border-radius:12px;font:14px system-ui";
    box.textContent = `Video Studio no pudo cargar su fuente completa: ${error.message}`;
    document.body.appendChild(box);
  });
})();
