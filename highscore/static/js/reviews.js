let activeModel = null;


async function updateInconsistentStats(modelName) {
    try {
        const encodedModel = encodeURIComponent(modelName);

        const userResp = await fetch(
            `${API_URL}/api/inconsistent/model/${encodedModel}/userstats`
        );
        const annotatorResp = await fetch(
            `${API_URL}/api/inconsistent/model/${encodedModel}/stats/annotators`
        );


        const userStats = await userResp.json();
        const annotatorStats = await annotatorResp.json();

        const has_sorted = Object.fromEntries(
            Object.entries(userStats.has)
                .sort((a, b) => b[1].total - a[1].total)
        );

        const was_sorted = Object.fromEntries(
            Object.entries(annotatorStats.was)
                .sort((a, b) => a[1].errorRate - b[1].errorRate)
        );

        renderUserGroup("reviewUserHas", has_sorted, false, true);
        renderUserGroup("reviewUserWas", was_sorted, true, true);

    } catch (err) {
        console.error("Failed to load inconsistent review stats:", err);
    }
}


async function renderReviewProgress(modelName, container) {
    const resp = await fetch(
        `${API_URL}/api/inconsistent/progress/${modelName}`
    );
    const data = await resp.json();

    const percent = (data.progress * 100).toFixed(1);

    container.innerHTML += `
        <div class="total-counter" style="margin-bottom:20px;">
            <div style="font-weight:600">${modelName}</div>
            Reviewed ${data.reviewed} / ${data.total}
            (${data.left} left) – ${percent}%
        </div>
    `;
}

function renderUserGroup(targetId, groupData, showErrorRate = false, showRank = false) {
    const container = document.getElementById(targetId);
    container.innerHTML = "";

    let rank = 1;

    Object.entries(groupData).forEach(([user, stats]) => {
        const row = document.createElement("div");
        row.className = "review-row";

        let html = "";

        if (showRank) {
            html += `<span>#${rank}</span>`;
        }

        html += `
            <span>${user}</span>
            <span>${stats.total}</span>
            <span>${stats.accepted}</span>
            <span>${stats.corrected}</span>
        `;

        if (showErrorRate) {
            const rate = (stats.errorRate * 100).toFixed(1) + "%";
            html += `<span>${rate}</span>`;
        }

        row.innerHTML = html;
        container.appendChild(row);

        rank++;
    });
}

async function renderAnnotatorProgress(modelName, container) {
    const resp = await fetch(
        `${API_URL}/api/inconsistent/progress/${modelName}/annotators`
    );
    const annotators = await resp.json();

    annotators.forEach(a => {
        const pct = (a.progress * 100).toFixed(1);

        container.innerHTML += `
            <div class="leaderboard-item">
                <div class="user-info">
                    <div class="username">${a.annotator}</div>
                    <div class="classes">
                        Reviewed ${a.reviewed} / ${a.total}
                        (${a.left} left)
                    </div>
                </div>
                <div class="score">${pct}%</div>
            </div>
        `;
    });
}


async function renderModelClassStats(modelName, container) {
    const resp = await fetch(
        `${API_URL}/api/inconsistent/modelstats/${modelName}/classes`
    );
    const classStats = await resp.json();

    classStats.sort((a, b) => a.errorRate - b.errorRate);

    classStats.forEach((stat, index) => {
        const errorPct = (stat.errorRate * 100).toFixed(1);

        container.innerHTML += `
            <div class="leaderboard-item">
                <div class="rank">#${index + 1}</div>
                <div class="user-info">
                    <div class="username">${stat.class}</div>
                    <div class="classes">
                        Correct ${stat.correct} / Incorrect ${stat.incorrect}
                    </div>
                </div>
                <div class="score">${errorPct}%</div>
            </div>
        `;
    });
}


async function renderModel(modelName) {
    // Oben: model-spezifischer Progress + Annotator-Progress
    const topContainer = document.getElementById("modelTabContent");
    topContainer.innerHTML = "";

    await renderReviewProgress(modelName, topContainer);
    await renderAnnotatorProgress(modelName, topContainer);

    // Unten: Model Class Performance
    const classContainer = document.getElementById("modelClassList");
    classContainer.innerHTML = "";
    await renderModelClassStats(modelName, classContainer);
}



async function initModelTabs() {
    const resp = await fetch("/api/inconsistent/modelstats");
    const models = await resp.json();

    const tabs = document.getElementById("modelTabs");
    tabs.innerHTML = "";

    models.forEach((model, index) => {
        const btn = document.createElement("button");
        btn.className = "model-tab";
        btn.textContent = model.modelName;

        if (index === 0) {
            btn.classList.add("active");
            activeModel = model.modelName;
        }

        btn.onclick = async () => {
            document.querySelectorAll(".model-tab")
                .forEach(b => b.classList.remove("active"));

            btn.classList.add("active");
            activeModel = model.modelName;

            await renderModel(activeModel);
            await updateInconsistentStats(activeModel);
        };

        tabs.appendChild(btn);
    });
}


document.addEventListener("DOMContentLoaded", async () => {
    await initModelTabs();

    if (!activeModel) {
        console.error("No activeModel after initModelTabs");
        return;
    }

    await renderModel(activeModel);
    await updateInconsistentStats(activeModel);
});

