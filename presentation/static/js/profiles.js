/**
 * Profile Manager for VoiceFlow PoC (F3)
 * Handles profile registry loading, LocalStorage persistence,
 * Bootstrap modal UI, and navbar badge.
 */

class ProfileManager {
    constructor() {
        this.profiles = [];
        this.activeProfileId = null;
        this.modalInstance = null;
        this.isLoaded = false;
    }

    async init() {
        await this.loadRegistry();
        this.loadFromLocalStorage();
        this.validateActiveProfile();
        this.buildModal();
        this.buildNavbarButton();
        this.updateBadge();
        this.isLoaded = true;
        console.log('ProfileManager initialized', {
            profileCount: this.profiles.length,
            activeProfileId: this.activeProfileId
        });
    }

    // ── Registry ──────────────────────────────────────────

    async loadRegistry() {
        try {
            const response = await fetch('/static/config/profiles.json');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            this.profiles = data.profiles || [];
        } catch (error) {
            console.warn('Failed to load profile registry:', error.message);
            this.profiles = [];
        }
    }

    // ── LocalStorage ──────────────────────────────────────

    loadFromLocalStorage() {
        try {
            this.activeProfileId = localStorage.getItem('vf_active_profile_id') || null;
        } catch {
            this.activeProfileId = null;
        }
    }

    saveToLocalStorage(profileId) {
        try {
            if (profileId) {
                localStorage.setItem('vf_active_profile_id', profileId);
                localStorage.setItem('vf_active_profile_updated_at', new Date().toISOString());
            } else {
                localStorage.removeItem('vf_active_profile_id');
                localStorage.removeItem('vf_active_profile_updated_at');
            }
        } catch (e) {
            console.warn('LocalStorage unavailable:', e.message);
        }
    }

    validateActiveProfile() {
        if (this.activeProfileId && !this.profiles.find(p => p.id === this.activeProfileId)) {
            console.warn('Stored profile_id not found in registry, clearing:', this.activeProfileId);
            this.activeProfileId = null;
            this.saveToLocalStorage(null);
        }
    }

    // ── Public API ────────────────────────────────────────

    getActiveProfileId() {
        return this.activeProfileId;
    }

    getProfileForRequest() {
        return { active_profile_id: this.activeProfileId };
    }

    setActiveProfile(profileId) {
        this.activeProfileId = profileId || null;
        this.saveToLocalStorage(this.activeProfileId);
        this.updateBadge();
        if (this.modalInstance) this.modalInstance.hide();
    }

    // ── Navbar Button ─────────────────────────────────────

    buildNavbarButton() {
        const navbarNav = document.querySelector('.navbar-nav.ms-auto');
        if (!navbarNav) return;

        const wrapper = document.createElement('span');
        wrapper.className = 'nav-link text-light d-flex align-items-center';
        wrapper.id = 'navbarPreferencesToggle';
        wrapper.style.cursor = 'pointer';
        wrapper.innerHTML = `
            <i class="bi bi-person-gear me-1"></i>
            <small>Preferencias</small>
            <span id="profileBadge" class="badge ms-2 d-none"></span>
        `;
        wrapper.addEventListener('click', () => this.openModal());

        // Insert before the existing environment mode span
        const existingSpan = navbarNav.querySelector('.nav-link');
        if (existingSpan) {
            navbarNav.insertBefore(wrapper, existingSpan);
        } else {
            navbarNav.appendChild(wrapper);
        }
    }

    // ── Badge ─────────────────────────────────────────────

    updateBadge() {
        const badge = document.getElementById('profileBadge');
        if (!badge) return;

        if (this.activeProfileId) {
            const profile = this.profiles.find(p => p.id === this.activeProfileId);
            if (profile) {
                badge.textContent = profile.label;
                badge.className = `badge ms-2 ${profile.ui?.badge_class || 'bg-secondary'}`;
                badge.classList.remove('d-none');
            } else {
                badge.classList.add('d-none');
            }
        } else {
            badge.classList.add('d-none');
        }
    }

    // ── Modal ─────────────────────────────────────────────

    buildModal() {
        // Remove existing modal if any (idempotent)
        const existing = document.getElementById('preferencesModal');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'preferencesModal';
        modal.tabIndex = -1;
        modal.setAttribute('aria-labelledby', 'preferencesModalLabel');
        modal.setAttribute('aria-hidden', 'true');

        const profileCards = this.profiles.length > 0
            ? this.profiles.map(p => this._buildProfileCard(p)).join('')
            : '<div class="alert alert-warning mb-0"><i class="bi bi-exclamation-triangle"></i> Perfiles no disponibles.</div>';

        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="preferencesModalLabel">
                            <i class="bi bi-person-gear"></i> Preferencias de Perfil
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p class="text-muted small mb-3">
                            Selecciona un perfil para personalizar las recomendaciones. El perfil prioriza ciertos resultados sin excluir otros.
                        </p>
                        <div id="profileOptionsContainer">
                            ${this._buildNoneOption()}
                            ${profileCards}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="button" class="btn btn-primary" id="saveProfileBtn">
                            <i class="bi bi-check-lg"></i> Guardar
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Wire save button
        document.getElementById('saveProfileBtn').addEventListener('click', () => {
            const selected = modal.querySelector('input[name="profileOption"]:checked');
            const selectedId = selected ? selected.value : null;
            this.setActiveProfile(selectedId === '__none__' ? null : selectedId);
        });

        // Wire click on card label (for better UX)
        modal.querySelectorAll('.profile-card-option').forEach(card => {
            card.addEventListener('click', () => {
                const radio = card.querySelector('input[type="radio"]');
                if (radio) {
                    radio.checked = true;
                    // Update visual selection
                    modal.querySelectorAll('.profile-card-option').forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                }
            });
        });

        this.modalInstance = new bootstrap.Modal(modal);
    }

    openModal() {
        if (!this.modalInstance) return;

        // Pre-select current active profile
        const container = document.getElementById('profileOptionsContainer');
        if (container) {
            container.querySelectorAll('.profile-card-option').forEach(c => c.classList.remove('selected'));
            const currentValue = this.activeProfileId || '__none__';
            const radio = container.querySelector(`input[value="${currentValue}"]`);
            if (radio) {
                radio.checked = true;
                radio.closest('.profile-card-option')?.classList.add('selected');
            }
        }

        this.modalInstance.show();
    }

    _buildNoneOption() {
        const isActive = !this.activeProfileId;
        return `
            <label class="profile-card-option d-flex align-items-center ${isActive ? 'selected' : ''}">
                <input type="radio" name="profileOption" value="__none__" ${isActive ? 'checked' : ''}>
                <span class="profile-icon"><i class="bi bi-x-circle"></i></span>
                <div>
                    <div class="profile-label">Ninguno</div>
                    <div class="profile-description">Sin perfil activo — comportamiento por defecto.</div>
                </div>
            </label>
        `;
    }

    _buildProfileCard(profile) {
        const isActive = this.activeProfileId === profile.id;
        const icon = profile.ui?.icon || 'bi-person';
        return `
            <label class="profile-card-option d-flex align-items-center ${isActive ? 'selected' : ''}">
                <input type="radio" name="profileOption" value="${profile.id}" ${isActive ? 'checked' : ''}>
                <span class="profile-icon"><i class="bi ${icon}"></i></span>
                <div>
                    <div class="profile-label">${profile.label}</div>
                    <div class="profile-description">${profile.description}</div>
                </div>
            </label>
        `;
    }
}

// Export for use in main app
window.ProfileManager = ProfileManager;
