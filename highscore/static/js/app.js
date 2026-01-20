
// Configuration
const API_URL = ''; // Will use same origin by default
const REFRESH_INTERVAL = 5000; // Refresh every 5 seconds



document.addEventListener("DOMContentLoaded", () => {
    // Initial load
    updateLeaderboard();
    // updateInconsistentStats();
    updateModelClassStats();
    updateTotalReviewed();
    updateAnnotatorProgress();

    // Auto-refresh
    setInterval(() => {
        updateLeaderboard();
        // updateInconsistentStats();
        updateModelClassStats();
        updateTotalReviewed();
        updateAnnotatorProgress();
    }, REFRESH_INTERVAL);
});


function initTabs() {
    const tabs = document.querySelectorAll(".tab");
    const contents = document.querySelectorAll(".tab-content");

    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            const target = tab.dataset.tab;

            tabs.forEach(t => t.classList.remove("active"));
            contents.forEach(c => c.classList.remove("active"));

            tab.classList.add("active");
            document.getElementById(`tab-${target}`).classList.add("active");
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initTabs();
});