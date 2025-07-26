// Tab switching functionality
        document.addEventListener('DOMContentLoaded', function() {
            const tabs = document.querySelectorAll('.tab');
            const tabContents = document.querySelectorAll('.tab-content');

            tabs.forEach(tab => {
                tab.addEventListener('click', function(e) {
                    e.preventDefault();
                    
                    // Remove active class from all tabs and contents
                    tabs.forEach(t => t.classList.remove('active'));
                    tabContents.forEach(content => content.classList.remove('active'));
                    
                    // Add active class to clicked tab
                    this.classList.add('active');
                    
                    // Show corresponding content
                    const platform = this.getAttribute('data-platform');
                    const targetContent = document.querySelector(`[data-content="${platform}"]`);
                    if (targetContent) {
                        targetContent.classList.add('active');
                    }
                });
            });

            // Create animated particles
            createParticles();
        });

        function showDownloadMessage(event) {
            const progressMessage = document.getElementById('progressMessage');
            const loading = progressMessage.querySelector('.loading');
            
            progressMessage.style.display = 'block';
            loading.style.display = 'block';
            
            // Add some visual feedback
            progressMessage.style.animation = 'slideUp 0.5s ease-out';
            
            // Optional: Hide after successful download (you can remove this if you want it to stay)
            setTimeout(() => {
                progressMessage.style.animation = 'fadeIn 0.5s ease-out reverse';
            }, 3000);
        }

        function createParticles() {
            const particlesContainer = document.getElementById('particles');
            const particleCount = 50;

            for (let i = 0; i < particleCount; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                
                // Random positioning
                particle.style.left = Math.random() * 100 + '%';
                particle.style.top = Math.random() * 100 + '%';
                
                // Random animation delay
                particle.style.animationDelay = Math.random() * 6 + 's';
                particle.style.animationDuration = (Math.random() * 4 + 4) + 's';
                
                particlesContainer.appendChild(particle);
            }
        }

        // Add smooth scrolling and enhanced interactions
        document.querySelectorAll('input').forEach(input => {
            input.addEventListener('focus', function() {
                this.parentElement.style.transform = 'scale(1.02)';
            });
            
            input.addEventListener('blur', function() {
                this.parentElement.style.transform = 'scale(1)';
            });
        });

        // Enhanced button interactions
        document.querySelectorAll('.download-btn').forEach(btn => {
            btn.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-3px) scale(1.05)';
            });
            
            btn.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
            });
        });