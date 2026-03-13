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

    /** Google Places type → Spanish label + icon */
    static TYPE_LABELS = {
        'restaurant': { label: 'Restaurante', icon: 'bi-cup-straw' },
        'mediterranean_restaurant': { label: 'Mediterráneo', icon: 'bi-cup-straw' },
        'italian_restaurant': { label: 'Italiano', icon: 'bi-cup-straw' },
        'japanese_restaurant': { label: 'Japonés', icon: 'bi-cup-straw' },
        'chinese_restaurant': { label: 'Chino', icon: 'bi-cup-straw' },
        'indian_restaurant': { label: 'Indio', icon: 'bi-cup-straw' },
        'mexican_restaurant': { label: 'Mexicano', icon: 'bi-cup-straw' },
        'seafood_restaurant': { label: 'Marisquería', icon: 'bi-cup-straw' },
        'fast_food_restaurant': { label: 'Comida rápida', icon: 'bi-cup-straw' },
        'cafe': { label: 'Cafetería', icon: 'bi-cup-hot' },
        'bar': { label: 'Bar', icon: 'bi-cup-straw' },
        'museum': { label: 'Museo', icon: 'bi-bank' },
        'art_gallery': { label: 'Galería de arte', icon: 'bi-palette' },
        'tourist_attraction': { label: 'Atracción turística', icon: 'bi-camera' },
        'park': { label: 'Parque', icon: 'bi-tree' },
        'amusement_park': { label: 'Parque de atracciones', icon: 'bi-emoji-laughing' },
        'theater': { label: 'Teatro', icon: 'bi-film' },
        'movie_theater': { label: 'Cine', icon: 'bi-film' },
        'shopping_mall': { label: 'Centro comercial', icon: 'bi-bag' },
        'hotel': { label: 'Hotel', icon: 'bi-building' },
        'church': { label: 'Iglesia', icon: 'bi-building' },
        'zoo': { label: 'Zoo', icon: 'bi-bug' },
        'aquarium': { label: 'Acuario', icon: 'bi-water' },
        'spa': { label: 'Spa', icon: 'bi-droplet' },
        'gym': { label: 'Gimnasio', icon: 'bi-bicycle' },
        'night_club': { label: 'Discoteca', icon: 'bi-music-note-beamed' },
        'library': { label: 'Biblioteca', icon: 'bi-book' },
        'visitor_center': { label: 'Centro de visitantes', icon: 'bi-info-circle' },
        'indoor_playground': { label: 'Parque infantil', icon: 'bi-emoji-smile' },
        'historical_landmark': { label: 'Monumento histórico', icon: 'bi-landmark' },
        'cultural_center': { label: 'Centro cultural', icon: 'bi-people' },
        'stadium': { label: 'Estadio', icon: 'bi-trophy' },
        'bakery': { label: 'Panadería', icon: 'bi-shop' },
        'food': { label: 'Gastronomía', icon: 'bi-egg-fried' },
        'point_of_interest': { label: 'Punto de interés', icon: 'bi-geo-alt' },
        'establishment': { label: 'Establecimiento', icon: 'bi-shop-window' },
    };

    /**
     * Convert raw Google Places types to readable Spanish badges.
     * Shows up to maxTags types, skipping generic ones if specific ones exist.
     */
    static renderTypeBadges(types, maxTags = 3) {
        if (!types || types.length === 0) return '';
        // Filter out overly generic types if we have specific ones
        const generic = new Set(['point_of_interest', 'establishment', 'food']);
        const specific = types.filter(t => !generic.has(t));
        const display = (specific.length > 0 ? specific : types).slice(0, maxTags);

        return display.map(t => {
            const info = CardRenderer.TYPE_LABELS[t] || { label: t.replace(/_/g, ' '), icon: 'bi-tag' };
            return `<span class="badge bg-light text-dark border me-1"><i class="bi ${info.icon}"></i> ${info.label}</span>`;
        }).join('');
    }

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
        const typeBadges = CardRenderer.renderTypeBadges(rec.types || [rec.type]);
        const confidencePercent = rec.confidence != null ? Math.round(rec.confidence * 100) : null;
        const confidenceBadge = confidencePercent != null
            ? `<span class="badge bg-info" title="Relevancia de la recomendación"><i class="bi bi-bullseye"></i> Relevancia: ${confidencePercent}%</span>`
            : '';
        // maps_url removed from header — directions links are per-route now
        // source badge removed — not user-facing value

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

        // Accessibility section — only show if there is meaningful data
        let accHtml = '';
        if (rec.accessibility) {
            const a = rec.accessibility;
            const aScore = a.score || 0;
            const hasServices = a.services && Object.keys(a.services).length > 0;
            const hasFacilities = a.facilities && a.facilities.length > 0;
            const hasLevel = a.level && a.level !== 'unknown' && a.level !== 'Unknown';
            const hasMeaningfulData = aScore > 0 || hasServices || hasFacilities || hasLevel;

            if (hasMeaningfulData) {
                const aPercent = (aScore / 10) * 100;
                const aColor = aScore >= 8 ? 'success' : aScore >= 6 ? 'warning' : 'danger';

                const servicesHtml = hasServices
                    ? Object.entries(a.services).map(([k, v]) => {
                        const icon = v === 'Sí' ? 'bi-check-circle-fill text-success' : 'bi-x-circle text-danger';
                        return `<span class="badge bg-light text-dark border me-1 mb-1"><i class="bi ${icon}"></i> ${k}</span>`;
                    }).join('')
                    : '';

                const facilitiesHtml = hasFacilities
                    ? a.facilities.map(f => {
                        const info = CardRenderer.FACILITY_ICONS[f] || { icon: 'bi-check-circle', label: f.replace(/_/g, ' ') };
                        return `<span class="badge facility-badge me-1 mb-1"><i class="bi ${info.icon}"></i> ${info.label}</span>`;
                    }).join('')
                    : '';

                // Score bar only if score > 0
                const scoreBarHtml = aScore > 0 ? `
                    <div class="d-flex align-items-center mb-1">
                        <small class="text-muted me-2"><i class="bi bi-universal-access"></i> Accesibilidad</small>
                        <div class="score-bar-container flex-grow-1 me-2">
                            <div class="score-bar"><div class="score-bar-fill bg-${aColor}" style="width: ${aPercent}%"></div></div>
                        </div>
                        <span class="badge bg-${aColor}">${aScore}/10</span>
                    </div>` : `
                    <div class="mb-1">
                        <small class="text-muted"><i class="bi bi-universal-access"></i> Accesibilidad</small>
                    </div>`;

                accHtml = `
                    <div class="rec-accessibility mt-2 pt-2 border-top">
                        ${scoreBarHtml}
                        ${hasLevel ? `<small class="text-muted">Nivel: <strong>${CardRenderer.escapeHtml(a.level.replace(/_/g, ' '))}</strong></small>` : ''}
                        ${servicesHtml ? `<div class="mt-1">${servicesHtml}</div>` : ''}
                        ${facilitiesHtml ? `<div class="mt-1">${facilitiesHtml}</div>` : ''}
                    </div>`;
            }
        }

        // Routes section
        let routesHtml = '';
        if (rec.routes && rec.routes.length > 0) {
            const routeItems = rec.routes.map(route => {
                const icon = CardRenderer.TRANSPORT_ICONS[route.transport] || 'bi-signpost-2';
                const accBadge = route.accessibility === 'full'
                    ? '<i class="bi bi-universal-access text-success"></i>'
                    : (route.accessibility === 'partial' ? '<i class="bi bi-universal-access text-warning"></i>' : '');
                const label = `<i class="bi ${icon}"></i> ${CardRenderer.escapeHtml(route.line || route.transport || '')}
                    ${route.duration ? `· ${CardRenderer.escapeHtml(route.duration)}` : ''}
                    ${accBadge}`;
                // Wrap in link if directions_url available
                if (route.directions_url) {
                    return `<a href="${CardRenderer.escapeHtml(route.directions_url)}" target="_blank" rel="noopener"
                        class="badge bg-light text-dark border me-1 mb-1 text-decoration-none"
                        title="Ver ruta en Google Maps">${label} <i class="bi bi-box-arrow-up-right small"></i></a>`;
                }
                return `<span class="badge bg-light text-dark border me-1 mb-1">${label}</span>`;
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
                            <i class="bi bi-building"></i>
                            ${rec.website_url
                                ? `<a href="${CardRenderer.escapeHtml(rec.website_url)}" target="_blank" rel="noopener" class="text-decoration-none">${name} <i class="bi bi-box-arrow-up-right small"></i></a>`
                                : name}
                        </h6>
                        <div class="mt-1">${typeBadges}</div>
                        <div>
                            ${confidenceBadge}
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
