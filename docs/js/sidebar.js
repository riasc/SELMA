(function() {
    const pages = [
        { id: 'drawhistory', label: 'Draw History', href: 'index.html', section: 'draws' },
        { id: 'profiles', label: 'Profiles', href: 'profiles.html', section: 'analysis' },
        { id: 'oddeven', label: 'Odd / Even', href: 'oddeven.html', section: 'analysis' },
        { id: 'numgroups', label: 'Number Groups', href: 'numgroups.html', section: 'analysis' },
        { id: 'sumrange', label: 'Sum Range', href: 'sumrange.html', section: 'analysis' },
        { id: 'distance', label: 'Recency', href: 'distance.html', section: 'analysis' },
        { id: 'consecutive', label: 'Consecutive', href: 'consecutive.html', section: 'analysis' },
        { id: 'hotcold', label: 'Hot / Cold', href: 'hotcold.html', section: 'analysis' },
        { id: 'gaps', label: 'Gaps', href: 'gaps.html', section: 'analysis' },
    ];

    const currentPage = document.body.getAttribute('data-page');
    const sidebar = document.getElementById('sidebar');

    let html = '<h1>SELMA</h1>';
    html += '<h2>Draws</h2><div class="section">';
    pages.filter(p => p.section === 'draws').forEach(p => {
        const cls = p.id === currentPage ? ' active' : '';
        html += '<a class="section-item' + cls + '" href="' + p.href + '">' + p.label + '</a>';
    });
    html += '</div>';
    html += '<h2>Analysis</h2><div class="section">';
    pages.filter(p => p.section === 'analysis').forEach(p => {
        const cls = p.id === currentPage ? ' active' : '';
        html += '<a class="section-item' + cls + '" href="' + p.href + '">' + p.label + '</a>';
    });
    html += '</div>';

    sidebar.innerHTML = html;
})();
