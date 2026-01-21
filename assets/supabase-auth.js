/**
 * Supabase Authentication for Dash
 *
 * This script handles client-side authentication with Supabase
 * and synchronizes auth state with Dash via dcc.Store
 */

// Supabase client initialization (will be set from Python)
window.SupabaseAuth = {
    client: null,
    config: null,

    /**
     * Initialize Supabase client
     * @param {string} url - Supabase project URL
     * @param {string} anonKey - Supabase anonymous key
     */
    init: function(url, anonKey) {
        if (!url || !anonKey) {
            console.log('Supabase not configured, auth disabled');
            return;
        }

        this.config = { url, anonKey };

        // Load Supabase JS library dynamically
        if (!window.supabase) {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
            script.onload = () => {
                this.client = window.supabase.createClient(url, anonKey);
                this.setupAuthListener();
                this.checkSession();
            };
            document.head.appendChild(script);
        } else {
            this.client = window.supabase.createClient(url, anonKey);
            this.setupAuthListener();
            this.checkSession();
        }
    },

    /**
     * Set up auth state change listener
     */
    setupAuthListener: function() {
        if (!this.client) return;

        this.client.auth.onAuthStateChange((event, session) => {
            console.log('Auth state changed:', event);

            // Update Dash store with new auth state
            const authStore = document.getElementById('store-auth-session');
            if (authStore && authStore._dashprivate_store) {
                authStore._dashprivate_store.setProps({
                    data: session ? {
                        access_token: session.access_token,
                        refresh_token: session.refresh_token,
                        user: {
                            id: session.user.id,
                            email: session.user.email,
                            name: session.user.user_metadata?.full_name || '',
                            picture: session.user.user_metadata?.avatar_url || ''
                        }
                    } : null
                });
            }

            // Handle navigation after auth state changes
            console.log('Current pathname:', window.location.pathname, 'Event:', event);

            // Use sessionStorage flag to prevent redirect loops
            const redirected = sessionStorage.getItem('auth_redirected');

            if (event === 'SIGNED_IN' && session) {
                // Clear the flag if we have a session
                sessionStorage.removeItem('auth_redirected');

                // Redirect to home if on login page (including OAuth callback)
                if (window.location.pathname === '/login' || window.location.hash.includes('access_token')) {
                    console.log('Redirecting from login to home');
                    window.location.href = '/';
                } else if (!redirected) {
                    // If session exists but we're showing login page, reload once
                    console.log('Session exists, reloading to update UI');
                    sessionStorage.setItem('auth_redirected', 'true');
                    window.location.reload();
                }
            } else if (event === 'SIGNED_OUT') {
                sessionStorage.removeItem('auth_redirected');
                // Redirect to login page on sign out
                if (window.location.pathname !== '/login') {
                    window.location.href = '/login';
                }
            }
        });
    },

    /**
     * Check for existing session on page load
     */
    checkSession: async function() {
        if (!this.client) return null;

        try {
            const { data: { session } } = await this.client.auth.getSession();

            // Sync session to Dash's localStorage store
            if (session) {
                const storeData = {
                    access_token: session.access_token,
                    refresh_token: session.refresh_token,
                    user: {
                        id: session.user.id,
                        email: session.user.email,
                        name: session.user.user_metadata?.full_name || '',
                        picture: session.user.user_metadata?.avatar_url || ''
                    }
                };
                localStorage.setItem('store-auth-session', JSON.stringify(storeData));
                console.log('Session synced to localStorage');
            } else {
                localStorage.removeItem('store-auth-session');
            }

            return session;
        } catch (error) {
            console.error('Error checking session:', error);
            return null;
        }
    },

    /**
     * Sign in with Google OAuth
     */
    signInWithGoogle: async function() {
        if (!this.client) {
            alert('認証が設定されていません');
            return;
        }

        try {
            const { data, error } = await this.client.auth.signInWithOAuth({
                provider: 'google',
                options: {
                    redirectTo: window.location.origin + '/login'
                }
            });

            if (error) throw error;
        } catch (error) {
            console.error('Sign in error:', error);
            alert('ログインに失敗しました: ' + error.message);
        }
    },

    /**
     * Sign out
     */
    signOut: async function() {
        if (!this.client) return;

        try {
            const { error } = await this.client.auth.signOut();
            if (error) throw error;
            window.location.href = '/login';
        } catch (error) {
            console.error('Sign out error:', error);
            alert('ログアウトに失敗しました: ' + error.message);
        }
    },

    /**
     * Get current user
     */
    getUser: async function() {
        if (!this.client) return null;

        try {
            const { data: { user } } = await this.client.auth.getUser();
            return user;
        } catch (error) {
            console.error('Error getting user:', error);
            return null;
        }
    },

    /**
     * Get current session
     */
    getSession: async function() {
        if (!this.client) return null;

        try {
            const { data: { session } } = await this.client.auth.getSession();
            return session;
        } catch (error) {
            console.error('Error getting session:', error);
            return null;
        }
    }
};

// Make functions available for Dash clientside callbacks
if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.supabase = {
    signInWithGoogle: function() {
        window.SupabaseAuth.signInWithGoogle();
        return window.dash_clientside.no_update;
    },
    signOut: function() {
        window.SupabaseAuth.signOut();
        return window.dash_clientside.no_update;
    }
};

// Auto-initialize from data attributes when this script loads
(function() {
    function initFromConfig() {
        var config = document.getElementById('supabase-config');
        if (config) {
            var url = config.getAttribute('data-url');
            var anonKey = config.getAttribute('data-anon-key');
            if (url && anonKey) {
                console.log('Auto-initializing Supabase Auth...');
                window.SupabaseAuth.init(url, anonKey);
                return true;
            }
        }
        return false;
    }

    // Try to init immediately (if DOM is already loaded)
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        // Small delay to ensure Dash has rendered the config element
        setTimeout(initFromConfig, 100);
    } else {
        // Wait for DOM to be ready
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(initFromConfig, 100);
        });
    }

    // Also try on load as a fallback
    window.addEventListener('load', function() {
        if (!window.SupabaseAuth.client) {
            initFromConfig();
        }
    });
})();
