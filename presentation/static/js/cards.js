/**
 * Rich Response Card Renderer for VoiceFlow PoC
 * Renders structured tourism data as Bootstrap cards inside chat messages.
 */

class CardRenderer {

    static FACILITY_ICONS = {
        'wheelchair_ramps': { icon: 'bi-person-wheelchair', label: 'Rampas' },
        'adapted_bathrooms': { icon: 'bi-droplet', label: 'Aseos adaptados' },
        'audio_guides': { icon: 'bi-headphones', label: 'Audioguias' },
        'tactile_paths': { icon: 'bi-hand-index', label: 'Rutas tactiles' },
        'sign_language_interpreters': { icon: 'bi-hand-thumbs-up', label: 'Lengua de signos' },
        'elevator_access': { icon: 'bi-arrow-up-square', label: 'Ascensor' },
        'wheelchair_spaces': { icon: 'bi-person-wheelchair', label: 'Espacios reservados' },
        'hearing_loops': { icon: 'bi-ear', label: 'Bucle auditivo' },
    };

    static TRANSPORT_ICONS = {
        'metro': 'bi-train-front',
        'bus': 'bi-bus-front',
        'taxi': 'bi-taxi-front',
        'walking': 'bi-person-walking',
    };

    /**
     * Render recommendation cards (Phase C: multi-place support).
     * Falls back to legacy tourism_data render when recommendations are empty.
     * @param {Array} recommendations - list of Recommendation objects
     * @returns {string} HTML string
     */
    static renderRecommendations(recommendations) {
        if (!recommendations || recommendations.length === 0) return '';

        let html = '<div class="response-cards recommendations-list mt-3">';

        recommendations.forEach((rec, index) => {
            html += CardRenderer._renderRecommendationCard(rec, index);
        });

        html += '</div>';
        return html;
    }

    /**
     * Render a single combined recommendation card (venue + accessibility + routes).
     */
    static _renderRecommendationCard(rec, index) {
        const name = CardRenderer.escapeHtml(rec.name || 'Recomendación');
        const type = CardRenderer.escapeHtml(rec.type || 'venue');
        const confidencePercent = rec.confidence != null ? Math.round(rec.confidence * 100) : null;
        const confidenceBadge = confidencePercent != null
            ? `<span class="badge bg-info"><i class="bi bi-bullseye"></i> ${confidencePercent}%</span>`
            : '';
        const mapsLink = rec.maps_url
            ? `<a href="${CardRenderer.escapeHtml(rec.maps_url)}" target="_blank" rel="noopener" class="btn btn-sm btn-outline-primary ms-2"><i class="bi bi-geo-alt"></i> Maps</a>`
            : '';
        const sourceBadge = rec.source
            ? `<span class="badge bg-light text-muted border ms-1">${CardRenderer.escapeHtml(rec.source)}</span>`
            : '';

        // Venue section
        let venueHtml = '';
        if (rec.venue) {
            const v = rec.venue;
            const score = v.accessibility_score || 0;
            const scoreColor = score >= 8 ? 'success' : score >= 6 ? 'warning' : 'danger';
            const facilitiesBadges = (v.facilities || []).map(f => {
                const info = CardRenderer.FACILITY_ICONS[f] || { icon: 'bi-check-circle', label: f.replace(/_/g, ' ') };
                return `<span class="badge facility-badge"><i class="bi ${info.icon}"></i> ${info.label}</span>`;
            }).join('');

            venueHtml = `
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div class="facilities-list">${facilitiesBadges}</div>
                    <div class="accessibility-gauge">
                        <div class="gauge-circle gauge-${scoreColor}">
                            <span class="gauge-value">${score}</span>
                            <span class="gauge-label">/10</span>
                        </div>
                    </div>
                </div>`;
        }

        // Accessibility section
        let accHtml = '';
        if (rec.accessibility) {
            const a = rec.accessibility;
            const aScore = a.score || 0;
            const aPercent = (aScore / 10) * 100;
            const aColor = aScore >= 8 ? 'success' : aScore >= 6 ? 'warning' : 'danger';
            const servicesHtml = a.services
                ? Object.entries(a.services).map(([k, v]) =>
                    `<span class="badge bg-light text-dark border me-1 mb-1"><i class="bi bi-check2"></i> ${k}: ${v}</span>`
                ).join('')
                : '';

            accHtml = `
                <div class="rec-accessibility mt-2 pt-2 border-top">
                    <div class="d-flex align-items-center mb-1">
                        <small class="text-muted me-2"><i class="bi bi-universal-access"></i> Accesibilidad</small>
                        <div class="score-bar-container flex-grow-1 me-2">
                            <div class="score-bar"><div class="score-bar-fill bg-${aColor}" style="width: ${aPercent}%"></div></div>
                        </div>
                        <span class="badge bg-${aColor}">${aScore}/10</span>
                    </div>
                    ${a.level ? `<small class="text-muted">Nivel: <strong>${CardRenderer.escapeHtml(a.level.replace(/_/g, ' '))}</strong></small>` : ''}
                    ${servicesHtml ? `<div class="mt-1">${servicesHtml}</div>` : ''}
                </div>`;
        }

        // Routes section
        let routesHtml = '';
        if (rec.routes && rec.routes.length > 0) {
            const routeItems = rec.routes.map(route => {
                const icon = CardRenderer.TRANSPORT_ICONS[route.transport] || 'bi-signpost-2';
                const accBadge = route.accessibility === 'full'
                    ? '<i class="bi bi-universal-access text-success"></i>'
                    : (route.accessibility === 'partial' ? '<i class="bi bi-universal-access text-warning"></i>' : '');
                return `<span class="badge bg-light text-dark border me-1 mb-1">
                    <i class="bi ${icon}"></i> ${CardRenderer.escapeHtml(route.line || route.transport || '')}
                    ${route.duration ? `· ${CardRenderer.escapeHtml(route.duration)}` : ''}
                    ${accBadge}
                </span>`;
            }).join('');

            routesHtml = `
                <div class="rec-routes mt-2 pt-2 border-top">
                    <small class="text-muted"><i class="bi bi-signpost-split"></i> Rutas</small>
                    <div class="mt-1">${routeItems}</div>
                </div>`;
        }

        return `
            <div class="card response-card recommendation-card mb-2" data-rec-id="${CardRenderer.escapeHtml(rec.id || '')}">
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h6 class="card-title mb-0">
                            <span class="badge bg-secondary rounded-pill me-1">${index + 1}</span>
                            <i class="bi bi-building"></i> ${name}
                            <small class="text-muted ms-1">${type}</small>
                        </h6>
                        <div>
                            ${confidenceBadge}
                            ${sourceBadge}
                            ${mapsLink}
                        </div>
                    </div>
                    ${venueHtml}
                    ${accHtml}
                    ${routesHtml}
                </div>
            </div>`;
    }

    /**
     * Render all applicable cards from tourism_data (legacy).
     * @param {Object} tourismData
     * @returns {string} HTML string
     */
    static render(tourismData) {
        if (!tourismData) return '';

        let html = '<div class="response-cards mt-3">';

        if (tourismData.venue) {
            html += CardRenderer.renderVenueCard(tourismData.venue);
        }

        if (tourismData.accessibility) {
            html += CardRenderer.renderAccessibilityCard(tourismData.accessibility);
        }

        if (tourismData.routes && tourismData.routes.length > 0) {
            html += CardRenderer.renderRouteCards(tourismData.routes);
        }

        html += '</div>';
        return html;
    }

    static renderVenueCard(venue) {
        const facilitiesBadges = (venue.facilities || []).map(f => {
            const info = CardRenderer.FACILITY_ICONS[f] || { icon: 'bi-check-circle', label: f.replace(/_/g, ' ') };
            return `<span class="badge facility-badge"><i class="bi ${info.icon}"></i> ${info.label}</span>`;
        }).join('');

        const score = venue.accessibility_score || 0;
        const scoreColor = score >= 8 ? 'success' : score >= 6 ? 'warning' : 'danger';

        const certBadge = venue.certification
            ? `<span class="badge bg-warning text-dark cert-badge"><i class="bi bi-award"></i> ${venue.certification.replace(/_/g, ' ')}</span>`
            : '';

        const hours = venue.opening_hours
            ? `<div class="venue-detail"><i class="bi bi-clock"></i> <small>${Object.entries(venue.opening_hours).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`).join(' | ')}</small></div>`
            : '';

        const pricing = venue.pricing
            ? `<div class="venue-detail"><i class="bi bi-tag"></i> <small>${Object.entries(venue.pricing).map(([k, v]) => `${k}: ${v}`).join(' | ')}</small></div>`
            : '';

        return `
            <div class="card response-card venue-card mb-2">
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <h6 class="card-title mb-1">
                                <i class="bi bi-building"></i> ${CardRenderer.escapeHtml(venue.name || 'Venue')}
                            </h6>
                            ${certBadge}
                        </div>
                        <div class="accessibility-gauge">
                            <div class="gauge-circle gauge-${scoreColor}">
                                <span class="gauge-value">${score}</span>
                                <span class="gauge-label">/10</span>
                            </div>
                        </div>
                    </div>
                    <div class="facilities-list mb-2">${facilitiesBadges}</div>
                    ${hours}
                    ${pricing}
                </div>
            </div>
        `;
    }

    static renderAccessibilityCard(accessibility) {
        const score = accessibility.score || 0;
        const scorePercent = (score / 10) * 100;
        const scoreColor = score >= 8 ? 'success' : score >= 6 ? 'warning' : 'danger';

        const servicesHtml = accessibility.services
            ? Object.entries(accessibility.services).map(([key, val]) =>
                `<div class="service-item"><i class="bi bi-check2"></i> <strong>${key.replace(/_/g, ' ')}:</strong> ${val}</div>`
            ).join('')
            : '';

        const certText = accessibility.certification
            ? `<span class="badge bg-secondary cert-badge"><i class="bi bi-shield-check"></i> ${accessibility.certification.replace(/_/g, ' ')}</span>`
            : '';

        return `
            <div class="card response-card accessibility-card mb-2">
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <h6 class="card-title mb-0">
                            <i class="bi bi-universal-access"></i> Accessibility
                        </h6>
                        ${certText}
                    </div>
                    <div class="d-flex align-items-center mb-2">
                        <div class="score-bar-container flex-grow-1 me-2">
                            <div class="score-bar">
                                <div class="score-bar-fill bg-${scoreColor}" style="width: ${scorePercent}%"></div>
                            </div>
                        </div>
                        <span class="badge bg-${scoreColor}">${score}/10</span>
                    </div>
                    <div class="small text-muted mb-1">
                        Level: <strong>${(accessibility.level || '').replace(/_/g, ' ')}</strong>
                    </div>
                    ${servicesHtml ? `<div class="services-list mt-2">${servicesHtml}</div>` : ''}
                </div>
            </div>
        `;
    }

    static renderRouteCards(routes) {
        return routes.map(route => {
            const icon = CardRenderer.TRANSPORT_ICONS[route.transport] || 'bi-signpost-2';

            const stepsHtml = (route.steps || []).map((step, i) =>
                `<div class="route-step"><span class="route-step-number">${i + 1}</span> ${CardRenderer.escapeHtml(step)}</div>`
            ).join('');

            const accessBadge = route.accessibility
                ? `<span class="badge ${route.accessibility === 'full' ? 'bg-success' : 'bg-warning text-dark'} mb-2"><i class="bi bi-universal-access"></i> ${route.accessibility} access</span>`
                : '';

            return `
                <div class="card response-card route-card mb-2">
                    <div class="card-body p-3">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h6 class="card-title mb-0">
                                <i class="bi ${icon}"></i>
                                ${CardRenderer.escapeHtml(route.line || route.transport || 'Route')}
                            </h6>
                            <div>
                                <span class="badge bg-info">${route.duration || '-'}</span>
                                <span class="badge bg-secondary">${route.cost || '-'}</span>
                            </div>
                        </div>
                        ${accessBadge}
                        <div class="route-steps">${stepsHtml}</div>
                    </div>
                </div>
            `;
        }).join('');
    }

    static escapeHtml(text) {
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return String(text).replace(/[&<>"']/g, m => map[m]);
    }
}

window.CardRenderer = CardRenderer;
