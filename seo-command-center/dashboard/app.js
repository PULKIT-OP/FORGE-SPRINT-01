/* app.js — SEO Command Center live cockpit. */
const $ = (id) => document.getElementById(id);
let totals = { High: 0, Medium: 0, Low: 0, total: 0 };

function log(msg, type = "system") {
    const l = $("log");
    if (l.querySelector(".empty-state")) l.innerHTML = "";
    const d = document.createElement("div");
    d.className = type;
    d.textContent = (type === "event" ? "⚡ " : "› ") + msg;
    l.appendChild(d);
    l.scrollTop = l.scrollHeight;
}

function addIssue(i) {
    const tb = $("tbody");
    if (tb.querySelector(".empty-state")) tb.innerHTML = "";
    const tr = document.createElement("tr");
    tr.innerHTML = `
        <td><span class="sev ${i.severity.toLowerCase()}">${i.severity}</span></td>
        <td style="font-weight:500">${i.type.replace(/_/g, ' ')}</td>
        <td style="text-align:center">${i.count}</td>
    `;
    tb.appendChild(tr);

    totals[i.severity] = (totals[i.severity] || 0) + 1;
    totals.total++;
    updateStats();
}

function updateStats() {
    $("c-total").textContent = totals.total;
    $("c-high").textContent = totals.High;
    $("c-med").textContent = totals.Medium;
    $("c-low").textContent = totals.Low;
}

function handle({ event, data }) {
    switch(event) {
        case "snapshot":
            if (data.site) {
                $("meta").textContent = "● " + data.site;
                $("urls").textContent = (data.urls || 0) + " URLs";
            }
            (data.issues || []).forEach(addIssue);
            break;
        case "loaded":
            $("meta").textContent = "● " + data.site;
            $("urls").textContent = data.urls + " URLs";
            log(`Loaded ${data.urls} URLs from ${data.site}`, "event");
            $("tbody").innerHTML = "";
            totals = { High:0, Medium:0, Low:0, total:0 };
            updateStats();
            break;
        case "issue":
            addIssue(data);
            log(`Detected ${data.count} instances of ${data.type.replace(/_/g, ' ')}`, "event");
            break;
        case "summary":
            log(`Audit complete. Identified ${data.total_issues} unique issue types.`, "event");
            break;
        case "fixes":
            log(`AI Fixer: Processed ${data.titles?.length || 0} titles and ${data.redirect_map?.length || 0} redirects.`, "event");
            break;
        case "exported":
            $("export").innerHTML = `
                <div class="export-banner">
                    <svg style="width:16px;height:16px" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                    report.html generated successfully ✓
                </div>
            `;
            log("Client deliverable (report.html) has been written to disk.", "event");
            break;
        case "saved":
            log("Report data synchronized to report.json", "system");
            break;
    }
}

const es = new EventSource("/events");
es.onmessage = (m) => { try { handle(JSON.parse(m.data)); } catch (e) { console.error("SSE Parse Error", e); } };
