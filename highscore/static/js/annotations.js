// Fetch and display leaderboard
async function updateLeaderboard() {
    try {
        const response = await fetch(`${API_URL}/api/leaderboard`);
        const data = await response.json();

        // Update total counter with animation
        const totalElement = document.getElementById('totalNumber');
        totalElement.classList.add('updating');
        totalElement.textContent = data.totalAnnotations.toLocaleString();
        setTimeout(() => totalElement.classList.remove('updating'), 1000);

        // Update leaderboard
        const leaderboardList = document.getElementById('leaderboardList');
        leaderboardList.innerHTML = '';

        data.leaderboard.forEach((user, index) => {
            const item = document.createElement('div');
            item.className = 'leaderboard-item';
            
            // Create class badges
            const classBadges = Object.entries(user.classes)
                .map(([className, count]) => 
                    `<span class="class-badge">${className}: ${count}</span>`
                )
                .join('');

            item.innerHTML = `
                <div class="rank rank-${index + 1}">#${index + 1}</div>
                <div class="user-info">
                    <div class="username">${user.username}</div>
                    <div class="classes">${classBadges}</div>
                </div>
                <div class="score">${user.total}</div>
            `;
            
            leaderboardList.appendChild(item);
        });

        // Update last updated time
        const lastUpdated = document.getElementById('lastUpdated');
        const updateTime = new Date(data.lastUpdated);
        lastUpdated.textContent = `Last updated: ${updateTime.toLocaleString()}`;

    } catch (error) {
        console.error('Failed to fetch leaderboard:', error);
        document.getElementById('leaderboardList').innerHTML = 
            '<p style="color: red;">Failed to load leaderboard. Please try again later.</p>';
    }
}