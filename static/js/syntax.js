function syntaxMode(mode) {
  if (mode === 'diagram') {
    document.querySelector('#icon-syntax').classList.remove('hidden');
    document.querySelector('#display-diagram').classList.remove('hidden');
    document.querySelector('#icon-diagram').classList.add('hidden');
    document.querySelector('#display-syntax').classList.add('hidden');
  } else {
    document.querySelector('#icon-diagram').classList.remove('hidden');
    document.querySelector('#display-syntax').classList.remove('hidden');
    document.querySelector('#icon-syntax').classList.add('hidden');
    document.querySelector('#display-diagram').classList.add('hidden');
  }
}

function toggleSyntax(evt) {
  const diagram = (evt.getAttribute('data-display') === 'diagram');
  const attr = diagram ? 'syntax' : 'diagram';
  evt.setAttribute('data-display', attr);
  syntaxMode(attr);
  if (window.localStorage) {
    window.localStorage.setItem('selectedSyntax', attr);
  } 
}

document.addEventListener('DOMContentLoaded', () => {
  if (window.localStorage) {
    const mode = window.localStorage.getItem('selectedSyntax') || 'syntax';
    document.querySelector('#syntax-button').setAttribute('data-display', mode);
    syntaxMode(mode);
  }
});