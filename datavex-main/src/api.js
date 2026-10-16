/**
 * DataVex API Client
 * Connects React frontend to FastAPI backend (http://localhost:8000)
 */

const API_BASE = 'http://localhost:8000/api/v1';

export async function getCompanies(sort = 'score', order = 'desc') {
    const res = await fetch(`${API_BASE}/companies?sort_by=${sort}&order=${order}&limit=50`);
    if (!res.ok) throw new Error(`Companies fetch failed: ${res.status}`);
    return res.json();
}

export async function getCompany(id) {
    const res = await fetch(`${API_BASE}/companies/${id}`);
    if (!res.ok) throw new Error(`Company fetch failed: ${res.status}`);
    return res.json();
}

export async function triggerDiscovery() {
    const res = await fetch(`${API_BASE}/discover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
    });
    if (res.status === 429) {
        const data = await res.json();
        throw new Error(data.detail || 'A scan is already running. Wait for it to finish.');
    }
    if (!res.ok) throw new Error(`Discovery failed: ${res.status}`);
    return res.json();
}

export async function getDiscoveryStatus(scanId) {
    const res = await fetch(`${API_BASE}/discover/${scanId}`);
    if (!res.ok) throw new Error(`Status check failed: ${res.status}`);
    return res.json();
}

export async function searchDiscover(companyName, domain = null) {
    const res = await fetch(`${API_BASE}/companies/search-discover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_name: companyName, domain }),
    });
    if (res.status === 429) {
        const data = await res.json();
        throw new Error(data.detail || 'A scan is already running.');
    }
    if (!res.ok) throw new Error(`Search discover failed: ${res.status}`);
    return res.json();
}
