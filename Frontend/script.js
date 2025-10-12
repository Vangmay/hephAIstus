// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Scroll to section function
function scrollToSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

// Process user input (simulated AI processing)
function processInput() {
    const input = document.getElementById('userInput');
    const output = document.getElementById('output');
    const userText = input.value.trim();
    
    if (!userText) {
        alert('Please enter some text to process');
        return;
    }
    
    // Show loading state
    output.innerHTML = '<div class="loading"></div> Processing your request...';
    output.classList.add('processing');
    
    // Simulate AI processing with a delay
    setTimeout(() => {
        const result = simulateAIProcessing(userText);
        displayResult(result);
    }, 2000);
}

// Simulate AI processing based on input
function simulateAIProcessing(input) {
    const lowerInput = input.toLowerCase();
    
    // Simple keyword-based responses for demonstration
    if (lowerInput.includes('hello') || lowerInput.includes('hi')) {
        return {
            type: 'greeting',
            content: `Hello! I'm HephAIstos.py, your AI-powered automation assistant. I can help you with various tasks using multiple AI models including Groq, Cerebras, and Exa APIs. What would you like me to help you with today?`
        };
    } else if (lowerInput.includes('automate') || lowerInput.includes('task')) {
        return {
            type: 'automation',
            content: `I can help automate various tasks using AI-powered decision making. Here are some examples:\n\n• Content generation and analysis\n• Data processing and insights\n• Web scraping and research\n• Code generation and debugging\n• Document summarization\n\nWhich type of task would you like to automate?`
        };
    } else if (lowerInput.includes('api') || lowerInput.includes('model')) {
        return {
            type: 'api_info',
            content: `HephAIstos.py integrates with multiple AI APIs:\n\n• Groq API: Fast inference for Llama models\n• Cerebras API: High-performance AI computing\n• Exa API: Advanced search capabilities\n\nEach API is configured through environment variables for secure access.`
        };
    } else if (lowerInput.includes('help') || lowerInput.includes('documentation')) {
        return {
            type: 'help',
            content: `Here's how to get started with HephAIstos.py:\n\n1. Install dependencies: pip install -r requirements.txt\n2. Configure API keys in .env file\n3. Run the application: python HephAIstos.py\n4. Start automating your tasks!\n\nFor detailed documentation, check the Documentation section below.`
        };
    } else {
        // Default response for unrecognized input
        return {
            type: 'default',
            content: `I received your input: "${input}"\n\nAs HephAIstos.py, I can help you with:\n• Task automation using AI\n• Content generation and analysis\n• Data processing and insights\n• Multi-model AI integration\n\nTry asking me about automation, APIs, or say 'hello' to get started!`
        };
    }
}

// Display the result in the output box
function displayResult(result) {
    const output = document.getElementById('output');
    
    let htmlContent = `<div class="result-header">${result.type.toUpperCase()}</div>\n`;
    htmlContent += `<div class="result-content">${escapeHtml(result.content)}</div>`;
    
    output.innerHTML = htmlContent;
    output.classList.remove('processing');
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Add some interactive features
document.addEventListener('DOMContentLoaded', function() {
    // Add typing animation to hero text
    const heroText = document.querySelector('.hero-content h2');
    const originalText = heroText.textContent;
    heroText.textContent = '';
    
    let i = 0;
    const typeWriter = () => {
        if (i < originalText.length) {
            heroText.textContent += originalText.charAt(i);
            i++;
            setTimeout(typeWriter, 100);
        }
    };
    
    // Start typewriter effect after a short delay
    setTimeout(typeWriter, 500);
    
    // Add parallax effect to hero section
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const hero = document.querySelector('.hero');
        if (hero) {
            hero.style.transform = `translateY(${scrolled * 0.5}px)`;
        }
    });
    
    // Add fade-in animation to feature cards
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // Observe feature cards
    document.querySelectorAll('.feature-card').forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(50px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });
});

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + Enter to process input
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const input = document.getElementById('userInput');
        if (document.activeElement === input) {
            processInput();
        }
    }
    
    // Escape to clear input
    if (e.key === 'Escape') {
        const input = document.getElementById('userInput');
        const output = document.getElementById('output');
        input.value = '';
        output.textContent = 'Results will appear here...';
    }
});

// Console easter egg
console.log(`
🚀 HephAIstos.py Website Loaded!

Available commands:
• processInput() - Process demo input
• scrollToSection('section-id') - Navigate to section

Keyboard shortcuts:
• Ctrl+Enter - Process input
• Escape - Clear input

Enjoy exploring HephAIstos.py!
`);