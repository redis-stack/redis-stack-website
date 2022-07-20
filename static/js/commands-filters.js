const FILTERS = {
  group: {
    element: document.querySelector('#group-filter'),
    oninput: () => {
      const { value } = FILTERS.group.element;
      if (setDisabledVersions(value)) return;
      FILTERS.version.element.value = '';
      const isCore = FILTERS.group.element.value && FILTERS.group.element.selectedOptions[0].dataset.kind === 'core';
      for (const option of FILTERS.version.element.options) {
        if (option.value.includes('-')) {
          option.style.display = option.value.startsWith(value) ? '' : 'none';
        } else {
          option.style.display = isCore ? '' : 'none';
        }
      }
    }
  },
  version: {
    element: document.querySelector('#version-filter'),
    versionMatch: true
  },
  name: {
    element: document.querySelector('#name-filter'),
    partialMatch: true
  }
};

const hiddenCards = [];

function setDisabledVersions(value) {
  return FILTERS.version.element.disabled = !value;
}

function isVersionGreaterThan(a, b) {
  const aSplit = a.split('.', 3),
    bSplit = b.split('.', 3);
  for (let i = 0; i < aSplit.length; i++) {
    const aNum = Number(aSplit[i]),
      bNum = Number(bSplit[i]);
    if (aNum < bNum) return true;
    else if (aNum > bNum) return false;
  }

  return true;
}

function match({ element: { value: filterValue }, versionMatch, partialMatch }, elementValue) {
  if (versionMatch) {
    const version = elementValue.substring(elementValue.lastIndexOf('-') + 1);
    return isVersionGreaterThan(version, filterValue);
  } else if (partialMatch) {
    return elementValue.toLowerCase().includes(filterValue.toLowerCase());
  } else {
    return filterValue === elementValue;
  }
}

function filter() {
  while (hiddenCards.length) {
    hiddenCards.pop().style.display = '';
  }

  for (const element of document.querySelectorAll('#commands-grid > [data-group]')) {
    for (const [key, filter] of Object.entries(FILTERS)) {
      if (!filter.element.value) continue;

      const elementValue = element.dataset[key];
      if (!match(filter, elementValue)) {
        element.style.display = 'none';
        hiddenCards.push(element);
        break;
      }
    }
  }
  // document.querySelector('#commands-break').style.display = hiddenCards.length > 0 ? 'none' : '';
}

const url = new URL(location);

function setUrl() {
  history.replaceState(null, '', url);
}

if (url.hash) {
  const value = url.hash.substring(1);
  url.searchParams.set('group', value);
  url.hash = '';
  setUrl();
}

for (const [key, { element, oninput }] of Object.entries(FILTERS)) {
  if (url.searchParams.has(key)) {
    element.value = url.searchParams.get(key);
  }

  element.addEventListener('input', () => {
    if (oninput) oninput();

    if (!element.value) {
      url.searchParams.delete(key);
    } else {
      url.searchParams.set(key, element.value);
    }

    setUrl();
    filter();
  });
}

for (const { oninput } of Object.values(FILTERS)) {
  if (oninput) oninput();
}

filter();