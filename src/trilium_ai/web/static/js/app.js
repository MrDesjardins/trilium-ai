// Trilium AI - Web Interface JavaScript

// DOM elements
const queryForm = document.getElementById('query-form');
const queryInput = document.getElementById('query-input');
const searchBtn = document.getElementById('search-btn');
const topKInput = document.getElementById('top-k');
const resultsDiv = document.getElementById('results');
const answerDiv = document.getElementById('answer');
const sourcesDiv = document.getElementById('sources');
const errorDiv = document.getElementById('error');
const examplesDiv = document.getElementById('examples');
const statusDiv = document.getElementById('status');
const btnText = searchBtn.querySelector('.btn-text');
const spinner = searchBtn.querySelector('.spinner');

// Check status on load
checkStatus();

// Event listeners
queryForm.addEventListener('submit', handleSubmit);

// Example chips
document.querySelectorAll('.example-chip').forEach(chip => {
    chip.addEventListener('click', () => {
        queryInput.value = chip.dataset.query;
        queryForm.dispatchEvent(new Event('submit'));
    });
});

// Check system status
async function checkStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        if (data.weaviate_connected) {
            statusDiv.textContent = `✓ Connected | ${data.total_chunks.toLocaleString()} chunks indexed`;
            statusDiv.className = 'status connected';
        } else {
            statusDiv.textContent = '✗ Disconnected from Weaviate';
            statusDiv.className = 'status disconnected';
        }
    } catch (error) {
        statusDiv.textContent = '✗ Error checking status';
        statusDiv.className = 'status disconnected';
    }
}

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();

    const query = queryInput.value.trim();
    if (!query) return;

    // Hide error and examples
    errorDiv.style.display = 'none';
    examplesDiv.style.display = 'none';

    // Show loading state
    setLoading(true);

    try {
        const requestBody = {
            query: query,
            top_k: parseInt(topKInput.value) || 5,
        };

        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Query failed');
        }

        const data = await response.json();
        displayResults(data);
    } catch (error) {
        displayError(error.message);
    } finally {
        setLoading(false);
    }
}

// Set loading state
function setLoading(loading) {
    searchBtn.disabled = loading;
    queryInput.disabled = loading;

    if (loading) {
        btnText.style.display = 'none';
        spinner.style.display = 'inline-block';
    } else {
        btnText.style.display = 'inline';
        spinner.style.display = 'none';
    }
}

// Display results
function displayResults(data) {
    // Display answer
    answerDiv.textContent = data.answer;

    // Display sources
    sourcesDiv.innerHTML = '';

    if (data.sources && data.sources.length > 0) {
        data.sources.forEach(source => {
            const card = document.createElement('div');
            card.className = 'source-card';

            const title = document.createElement('h3');
            if (source.url) {
                const link = document.createElement('a');
                link.href = source.url;
                link.target = '_blank';
                link.textContent = source.title;
                title.appendChild(link);
            } else {
                title.textContent = source.title;
            }
            card.appendChild(title);

            if (source.path) {
                const path = document.createElement('div');
                path.className = 'path';
                path.textContent = source.path;
                card.appendChild(path);
            }

            sourcesDiv.appendChild(card);
        });
    } else {
        sourcesDiv.innerHTML = '<p>No sources found</p>';
    }

    // Show results
    resultsDiv.style.display = 'block';

    // Scroll to results
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Display error
function displayError(message) {
    errorDiv.textContent = `Error: ${message}`;
    errorDiv.style.display = 'block';
    resultsDiv.style.display = 'none';

    // Scroll to error
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Auto-focus on input
queryInput.focus();
