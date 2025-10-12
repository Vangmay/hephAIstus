// HephAIstos site interactivity

// Add smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    document.querySelector(this.getAttribute('href')).scrollIntoView({
      behavior: 'smooth'
    });
  });
});

// Simple typewriter effect for header subtitle
const subtitle = document.querySelector('header p');
const text = subtitle.textContent;
subtitle.textContent = '';
let i = 0;
const type = () => {
  if (i < text.length) {
    subtitle.textContent += text.charAt(i);
    i++;
    setTimeout(type, 80);
  }
};
type();

// Copy code snippet on click
document.querySelectorAll('code').forEach(block => {
  block.style.cursor = 'pointer';
  block.title = 'Click to copy';
  block.addEventListener('click', () => {
    navigator.clipboard.writeText(block.textContent).then(() => {
      const original = block.textContent;
      block.textContent = 'Copied!';
      setTimeout(() => block.textContent = original, 1200);
    });
  });
});