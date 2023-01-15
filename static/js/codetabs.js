// TODO: URI-able tabs

function copyCodeToClipboard(panelId) {
  const code = document.querySelector(`${panelId} code`).textContent;
  const tooltip = document.querySelector(`${panelId} .tooltiptext`);
  navigator.clipboard.writeText(code);
  tooltip.style.display = "block";
  setTimeout(() => {
    tooltip.style.display = "none";
  }, 1000)
}

function switchCodeTab(tabGroup, tabId) {
  // Synchronize tab selection to relevant page tabs
  for (const tv of document.querySelectorAll('.codetabs')) {
    if (tv.id === tabGroup) continue; // Skip caller
    const trg = document.getElementById(`${tabId}_${tv.id}`);
    if (!trg) continue; // Skip tabs where there's no target
    for (const r of tv.querySelectorAll('input[type="radio"]')) {
      r.checked = (trg.id === r.id);
    }
  }

  // Persist tab selection
  if (window.localStorage) {
    window.localStorage.setItem('selectedCodeTab', tabId);
  }
}

function onchangeCodeTab(e) {
  const tabGroup = e.target.parentElement.id;
  const tabId = e.target.parentElement.querySelector(`label[for="${e.srcElement.id}"]`).textContent;
  const yPos = e.target.getBoundingClientRect().top;

  switchCodeTab(tabGroup, tabId);

  // Scroll to the source element if it jumped
  const yDiff = e.target.getBoundingClientRect().top - yPos;
  window.scrollTo(window.scrollX, window.scrollY + yDiff);
}

document.addEventListener('DOMContentLoaded', () => {
  for (const tvr of document.querySelectorAll('.codetabs > input[type="radio"]')) {
    tvr.addEventListener("change", (e) => onchangeCodeTab(e));
  }

  // Restore selection
  if (window.localStorage) {
    const selectedTab = window.localStorage.getItem("selectedCodeTab");
    if (selectedTab) {
      switchCodeTab(null, selectedTab);
    }
  }
});
