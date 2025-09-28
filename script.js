// Loading screen
window.addEventListener("load", () => {
  document.getElementById("loading-screen").style.display = "none";
});

// Scroll fade-in
const sections = document.querySelectorAll(".fade-in");
window.addEventListener("scroll", () => {
  const scrollTop = window.scrollY;
  const docHeight = document.body.scrollHeight - window.innerHeight;
  document.getElementById("progress-bar").style.width = (scrollTop/docHeight*100) + "%";
  
  sections.forEach(sec => {
    const rect = sec.getBoundingClientRect();
    if(rect.top < window.innerHeight - 100) sec.classList.add("visible");
  });
});

// Dark/Light mode
const toggleBtn = document.getElementById("theme-toggle");
toggleBtn.addEventListener("click", () => {
  document.body.classList.toggle("dark");
  toggleBtn.textContent = document.body.classList.contains("dark") ? "☀️" : "🌙";
});

// Burger menu for mobile
const burger = document.querySelector(".burger");
const navLinks = document.querySelector(".nav-links");
burger.addEventListener("click", () => {
  navLinks.classList.toggle("active
