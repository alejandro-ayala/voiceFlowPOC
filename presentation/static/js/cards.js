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
     * Render all applicable cards from tourism_data.
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
