/**
 * Audio notification system for Hamilton TMS
 * Provides pleasant C4-E4-G4 major chord chimes for class accounts
 * Handles iOS/iPad audio requirements and user interaction policies
 */

class AudioNotificationSystem {
    constructor() {
        this.audioContext = null;
        this.isInitialized = false;
        this.isClassAccount = false;
        this.masterVolume = 0.3; // Gentle volume level
        this.chordNotes = [261.63, 329.63, 392.00]; // C4, E4, G4 frequencies
        this.isSupported = this.checkAudioSupport();
        
        this.init();
    }
    
    checkAudioSupport() {
        return !!(window.AudioContext || window.webkitAudioContext);
    }
    
    init() {
        // Check if this is a class account by looking for class-specific elements or URL patterns
        this.detectClassAccount();
        
        console.log('Audio System: Initialization - Class account:', this.isClassAccount, 'Supported:', this.isSupported);
        
        if (this.isClassAccount && this.isSupported) {
            console.log('Audio System: Starting setup for class account');
            this.setupAudioContext();
            this.setupUserInteractionListener();
        } else {
            console.log('Audio System: Skipping setup -', 
                       !this.isClassAccount ? 'Not a class account' : 'Audio not supported');
        }
    }
    
    detectClassAccount() {
        // First check for direct server-side variable (most reliable)
        if (typeof window.isClassAccount !== 'undefined') {
            this.isClassAccount = window.isClassAccount;
            console.log('Audio System: Class account status from server:', this.isClassAccount);
            return;
        }
        
        // Check URL for class patterns or look for class-specific elements
        const url = window.location.pathname;
        const body = document.body;
        
        // Debug logging
        console.log('Audio System: Checking for class account...');
        console.log('Audio System: URL:', url);
        console.log('Audio System: Body classes:', body.classList.toString());
        console.log('Audio System: data-account-type element:', document.querySelector('[data-account-type="class"]'));
        
        // Class accounts typically have specific URL patterns or body classes
        this.isClassAccount = url.includes('/class') || 
                             body.classList.contains('class-account') ||
                             document.querySelector('[data-account-type="class"]') !== null ||
                             // Check for class-specific elements in the page
                             document.querySelector('.class-account-indicator') !== null;
        
        console.log('Audio System: Class account detected:', this.isClassAccount);
        
        // If still not detected, check if current user is not admin (fallback method)
        if (!this.isClassAccount) {
            // Look for admin-specific elements to determine if this is NOT an admin account
            const adminElements = document.querySelectorAll('[href*="/schools"], [href*="/students"], .admin-only');
            const hasAdminElements = adminElements.length > 0;
            
            // If no admin elements found, likely a class account
            if (!hasAdminElements && (url.includes('/routes') || url.includes('/dashboard'))) {
                this.isClassAccount = true;
                console.log('Audio System: Class account detected via fallback method');
            }
        }
    }
    
    setupAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            console.log('Audio System: AudioContext created successfully');
        } catch (error) {
            console.warn('Audio System: Failed to create AudioContext:', error);
            this.isSupported = false;
        }
    }
    
    setupUserInteractionListener() {
        // iOS requires user interaction before audio can play
        const events = ['touchstart', 'touchend', 'mousedown', 'keydown', 'click'];
        
        const initAudio = () => {
            if (this.audioContext && this.audioContext.state === 'suspended') {
                this.audioContext.resume().then(() => {
                    this.isInitialized = true;
                    console.log('Audio System: Initialized after user interaction');
                    // Remove listeners after first successful initialization
                    events.forEach(event => {
                        document.removeEventListener(event, initAudio);
                    });
                });
            } else if (this.audioContext && this.audioContext.state === 'running') {
                this.isInitialized = true;
                console.log('Audio System: Already running');
                events.forEach(event => {
                    document.removeEventListener(event, initAudio);
                });
            }
        };
        
        events.forEach(event => {
            document.addEventListener(event, initAudio, { once: true });
        });
    }
    
    createTone(frequency, duration = 0.3, startTime = 0) {
        if (!this.audioContext || !this.isInitialized) {
            return null;
        }
        
        try {
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            oscillator.frequency.setValueAtTime(frequency, this.audioContext.currentTime + startTime);
            oscillator.type = 'sine'; // Gentle sine wave for pleasant sound
            
            // Create gentle attack and release envelope
            const now = this.audioContext.currentTime + startTime;
            gainNode.gain.setValueAtTime(0, now);
            gainNode.gain.linearRampToValueAtTime(this.masterVolume, now + 0.05); // 50ms attack
            gainNode.gain.setValueAtTime(this.masterVolume, now + duration - 0.1);
            gainNode.gain.linearRampToValueAtTime(0, now + duration); // 100ms release
            
            oscillator.start(now);
            oscillator.stop(now + duration);
            
            return oscillator;
        } catch (error) {
            console.warn('Audio System: Error creating tone:', error);
            return null;
        }
    }
    
    playChord() {
        if (!this.canPlayAudio()) {
            return;
        }
        
        console.log('Audio System: Playing notification chime');
        
        // Play C4-E4-G4 major chord with slight stagger for richness
        this.chordNotes.forEach((frequency, index) => {
            this.createTone(frequency, 0.6, index * 0.02); // Slight stagger
        });
    }
    
    canPlayAudio() {
        return this.isClassAccount && 
               this.isSupported && 
               this.isInitialized && 
               this.audioContext && 
               this.audioContext.state === 'running';
    }
    
    // Public methods for triggering notifications
    onRouteStatusChange() {
        console.log('Audio System: onRouteStatusChange triggered');
        console.log('Audio System: Can play audio:', this.canPlayAudio());
        if (this.canPlayAudio()) {
            console.log('Audio System: Playing chord for route status change');
            this.playChord();
        } else {
            console.log('Audio System: Cannot play audio - requirements not met');
        }
    }
    
    onBulkOperation() {
        console.log('Audio System: onBulkOperation triggered');
        console.log('Audio System: Can play audio:', this.canPlayAudio());
        if (this.canPlayAudio()) {
            console.log('Audio System: Playing chord for bulk operation');
            this.playChord();
        } else {
            console.log('Audio System: Cannot play audio - requirements not met');
        }
    }
    
    // Test method for verification
    testAudio() {
        console.log('Audio System: Testing audio...');
        console.log('- Class account:', this.isClassAccount);
        console.log('- Supported:', this.isSupported);
        console.log('- Initialized:', this.isInitialized);
        console.log('- AudioContext state:', this.audioContext?.state);
        
        if (this.canPlayAudio()) {
            this.playChord();
            return true;
        } else {
            console.log('Audio System: Cannot play audio - requirements not met');
            return false;
        }
    }
}

// Initialize audio system when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Audio System: DOM loaded, initializing...');
    window.audioSystem = new AudioNotificationSystem();
    
    // For debugging - make test function available in console
    window.testAudio = () => window.audioSystem.testAudio();
    
    // Make detailed debug info available in console
    window.audioDebug = () => {
        console.log('=== Audio System Debug Info ===');
        console.log('Class account:', window.audioSystem.isClassAccount);
        console.log('Supported:', window.audioSystem.isSupported);
        console.log('Initialized:', window.audioSystem.isInitialized);
        console.log('AudioContext state:', window.audioSystem.audioContext?.state);
        console.log('Window variables:', {
            isClassAccount: window.isClassAccount,
            accountType: window.accountType
        });
        console.log('Body attributes:', {
            dataAccountType: document.body.getAttribute('data-account-type'),
            classes: document.body.classList.toString()
        });
        console.log('========================');
    };
    
    console.log('Audio System: Initialization complete. Use audioDebug() for detailed info.');
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioNotificationSystem;
}