// console.log('Read versions from json');

const version_json = '/versions.json';
const myRequest = new Request("/versions.json");

fetch(myRequest)
  .then((response) => response.json())
  .then((data) => {
    // console.log(data);
    const versionSelector = document.getElementById('docs-versions');

    const versionTypes = new Set(data.map(item => item.type));
    for (const vtype of versionTypes) {
      // Add description list
      const dl = document.createElement('dl');
      // <dl>
      // <dt><i class="bi bi-tags-fill version-header"></i>Versions</dt>
      // <dd><a href="{{ item.slug }}">{{ item.name }}</a></dd>
      // </dl>

      // Description item title
      const dt = document.createElement('dt');
      const icon = document.createElement('i');
      icon.classList.add('bi', 'version-header');
      switch (vtype) {
        case 'Tag':
          icon.classList.add('bi-tags-fill');
          break;
        case 'Branch':
          icon.classList.add('bi-git');
          break;
        default:
          icon.classList.add('bi-book-half');
      };

      dt.appendChild(icon)
      dt.appendChild(document.createTextNode(vtype));
      dl.appendChild(dt);

      for (const item of data) {
        if (item.type !== vtype) {
          continue;
        };
        // Description item
        const dd = document.createElement('dd');
        const ref = document.createElement('a');
        ref.setAttribute('href', item.slug);
        ref.appendChild(document.createTextNode(item.name));
        if (item.aliases && item.aliases.length > 0) {
          const aliases = document.createElement('strong');
          const aliasesText = document.createTextNode(
            '(' + item.aliases.toString() + ')'
          );
          aliases.appendChild(aliasesText);
          ref.appendChild(aliases);
        };
        dd.appendChild(ref);
        dl.appendChild(dd);
      };

      versionSelector.appendChild(dl);
    };
  })
  .catch(console.error);
