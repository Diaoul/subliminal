console.log('READ JS');
$(document).ready(function () {
    console.log('DOCUMENT DONE');

    $.getJSON('../versions.json', function (data) {
        console.log('JSON DECODE');
        if (data.length > 0) {
            var versions = [];
            $.each(data, function (index, value) {
                versions.push(value);
            });
            console.log('HERE WE ARE');
            var dl = document.getElementById('docs-versions');
            var all_versions = [];
            $.each(versions, function (i, v) {
                var version = versions[i];
                var element = '<dd><a href="' + version.slug + '">' + version.name + '</a></dd>';
                sorted_versions.push([version.name, element]);
                if (version.aliases) {
                    $.each(version.aliases, function (idx, alias) {
                        element = '<dd><a href="' + version.slug + '">' + alias + '</a></dd>';
                        sorted_versions.push([alias, element]);
                    });
                }
            });
            const tag_re = /v?\d+(\.\d+)?(\.\d+)?/g;
            dl.innerHTML = dl.innerHTML +
                '<dl><dt><i class="bi bi-tags-fill version-header"></i>Versions</dt>'
            $.each(all_versions, function (i, v) {
                var name = all_versions[i][0];
                var element = all_versions[i][1];
                if (name.match(tag_re)){
                    dl.innerHTML = dl.innerHTML + element;
                } else {
                    dl.innerHTML = dl.innerHTML + element;
                };
            });
            dl.innerHTML = dl.innerHTML + '</dl>'
        };
    });
});
