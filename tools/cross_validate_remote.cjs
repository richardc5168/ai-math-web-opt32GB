const fs = require('fs');
const path = require('path');
const vm = require('vm');
const crypto = require('crypto');

// Configuration
const REPO_ROOT = path.resolve(__dirname, '..');
const DOCS_ROOT = path.join(REPO_ROOT, 'docs');
const BASE_URL = 'https://richardc5168.github.io/ai-math-web';

const MODULES = {
    "fraction-g5": "bank.js",
    "fraction-word-g5": "bank.js",
    "decimal-unit4": "bank.js",
    "volume-g5": "bank.js",
    "ratio-percent-g5": "bank.js",
    "life-applications-g5": "bank.js",
    "g5-grand-slam": "bank.js",
    "offline-math": "bank.js",
    "interactive-decimal-g5": "bank.js",
    "interactive-g5-empire": "bank.js",
    "interactive-g5-life-pack1-empire": "bank.js",
    "interactive-g5-life-pack1plus-empire": "bank.js",
    "interactive-g5-life-pack2-empire": "bank.js",
    "interactive-g5-life-pack2plus-empire": "bank.js",
    "interactive-g56-core-foundation": "g56_core_foundation.json", // This one is tricky if it's pure JSON
    "exam-sprint": "bank.js",
    "commercial-pack1-fraction-sprint": "bank.js"
};

// Helper: Compute SHA-256 hash of a simplified object string
function computeHash(obj) {
    // We stringify with sorting keys to ensure deterministic output
    const str = JSON.stringify(obj, Object.keys(obj).sort()); 
    // Wait, simple JSON.stringify might not be stable enough if keys are unordered deep down.
    // But for this purpose (detecting matching content), usually sufficient if the structure is consistent.
    // A better approach is to rely on strict deep equality or a stable stringify.
    // Let's use a simple recursive sorter.
    return crypto.createHash('sha256').update(canonicalize(obj)).digest('hex');
}

function canonicalize(obj) {
    if (obj === null || typeof obj !== 'object') {
        return JSON.stringify(obj);
    }
    if (Array.isArray(obj)) {
        return '[' + obj.map(canonicalize).join(',') + ']';
    }
    const keys = Object.keys(obj).sort();
    return '{' + keys.map(k => JSON.stringify(k) + ':' + canonicalize(obj[k])).join(',') + '}';
}

function extractData(content, filename) {
    if (filename.endsWith('.json')) {
        return JSON.parse(content);
    }
    
    // For JS files that do `window.BANK_NAME = [...]`
    const sandbox = { window: {} };
    vm.createContext(sandbox);
    try {
        vm.runInContext(content, sandbox);
    } catch (e) {
        console.error(`Error executing ${filename}:`, e.message);
        return null;
    }
    
    // Find the property added to window
    const keys = Object.keys(sandbox.window);
    if (keys.length === 0) return null;
    // Assuming the first key is the bank. or checking typical names.
    // The previous python script had a mapping, but here we can just grab the first non-standard property?
    // Let's just grab the first key that looks like a bank array.
    for (const key of keys) {
        if (Array.isArray(sandbox.window[key])) {
            return sandbox.window[key];
        }
    }
    return sandbox.window[keys[0]]; // Fallback
}

async function validate() {
    console.log(`Starting Rigorous Remote Cross-Validation...`);
    console.log(`Repository: ${REPO_ROOT}`);
    console.log(`Remote Base: ${BASE_URL}\n`);

    let passCount = 0;
    let failCount = 0;
    
    for (const [moduleName, filename] of Object.entries(MODULES)) {
        const localPath = path.join(DOCS_ROOT, moduleName, filename);
        const remoteUrl = `${BASE_URL}/${moduleName}/${filename}`;

        process.stdout.write(`Checking [${moduleName}]... `);

        // 1. Read Local
        try {
            if (!fs.existsSync(localPath)) {
                console.log(`❌ FAIL (Local file missing: ${localPath})`);
                failCount++;
                continue;
            }
            const localRaw = fs.readFileSync(localPath, 'utf8');
            const localData = extractData(localRaw, filename);
            
            if (!localData) {
                console.log(`❌ FAIL (Could not extract data from local file)`);
                failCount++;
                continue;
            }

            // 2. Fetch Remote
            const res = await fetch(remoteUrl);
            if (!res.ok) {
                console.log(`❌ FAIL (Remote fetch error: ${res.status} ${res.statusText})`);
                failCount++;
                continue;
            }
            const remoteRaw = await res.text();
            const remoteData = extractData(remoteRaw, filename);
            
            if (!remoteData) {
                console.log(`❌ FAIL (Could not extract data from remote file)`);
                failCount++;
                continue;
            }

            // 3. Compare
            const localHash = computeHash(localData);
            const remoteHash = computeHash(remoteData);
            const localCount = Array.isArray(localData) ? localData.length : '?';
            const remoteCount = Array.isArray(remoteData) ? remoteData.length : '?';

            if (localHash === remoteHash) {
                console.log(`✅ MATCH (Items: ${localCount})`);
                passCount++;
            } else {
                console.log(`❌ MISMATCH!`);
                console.log(`   Local items: ${localCount}, Hash: ${localHash.substring(0,8)}...`);
                console.log(`   Remote items: ${remoteCount}, Hash: ${remoteHash.substring(0,8)}...`);
                failCount++;
            }

        } catch (err) {
            console.log(`❌ ERROR: ${err.message}`);
            failCount++;
        }
    }

    console.log(`\n---------------------------------------------------`);
    console.log(`SUMMARY: ${passCount} PASSED, ${failCount} FAILED`);
    console.log(`---------------------------------------------------`);
    
    if (failCount > 0) process.exit(1);
}

validate();
