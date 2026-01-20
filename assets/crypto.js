/**
 * Simple encryption/decryption for API keys
 * Uses XOR cipher with a fixed key for obfuscation.
 * Note: This is NOT cryptographically secure, but provides
 * basic protection against casual inspection of localStorage.
 */

window.CryptoUtils = {
    // Fixed key for XOR cipher (obfuscation purpose)
    KEY: 'TaxReturnApp2024SecureObfuscation',

    // XOR encrypt/decrypt (symmetric)
    xorCipher: function(input, key) {
        if (!input) return '';

        let output = '';
        for (let i = 0; i < input.length; i++) {
            const charCode = input.charCodeAt(i) ^ key.charCodeAt(i % key.length);
            output += String.fromCharCode(charCode);
        }
        return output;
    },

    // Encode to Base64 (for safe storage)
    toBase64: function(str) {
        try {
            return btoa(unescape(encodeURIComponent(str)));
        } catch (e) {
            return '';
        }
    },

    // Decode from Base64
    fromBase64: function(b64) {
        try {
            return decodeURIComponent(escape(atob(b64)));
        } catch (e) {
            return '';
        }
    },

    // Encrypt: XOR then Base64 encode
    encrypt: function(plaintext) {
        if (!plaintext) return '';
        const xored = this.xorCipher(plaintext, this.KEY);
        return this.toBase64(xored);
    },

    // Decrypt: Base64 decode then XOR
    decrypt: function(ciphertext) {
        if (!ciphertext) return '';
        const decoded = this.fromBase64(ciphertext);
        if (!decoded) return '';
        return this.xorCipher(decoded, this.KEY);
    },

    // Check if a string looks encrypted (Base64 format)
    isEncrypted: function(str) {
        if (!str) return false;
        // Check if it's valid Base64 and doesn't look like a raw API key
        try {
            const decoded = atob(str);
            // If it decodes and re-encodes to same value, it's likely encrypted
            return btoa(decoded) === str && str.length > 20;
        } catch (e) {
            return false;
        }
    }
};

// Make it available globally for Dash clientside callbacks
if (!window.dash_clientside) {
    window.dash_clientside = {};
}
window.dash_clientside.crypto = window.CryptoUtils;
