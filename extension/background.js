// Background service worker for Sign Language Translator extension
chrome.runtime.onInstalled.addListener(() => {
  console.log('Sign Language Translator extension installed');
  chrome.storage.local.set({
    extensionEnabled: false,
    backendUrl: 'http://localhost:5000',
    gifDuration: 1500
  });
});

chrome.action.onClicked.addListener((tab) => {
  console.log('Extension icon clicked for tab:', tab.id);
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Background received message:', message);
  if (message.action === 'log') {
    console.log('Content script log:', message.data);
    sendResponse({ success: true });
    return true;
  }
  if (message.action === 'error') {
    console.error('Content script error:', message.error);
    sendResponse({ success: true });
    return true;
  }
  if (message.action === 'checkBackend') {
    checkBackendHealth()
      .then(result => sendResponse(result))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }
  return true;
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url &&
      (tab.url.includes('youtube.com') || tab.url.includes('netflix.com') ||
       tab.url.includes('video') || tab.url.includes('watch'))) {
    console.log('Video page detected, preparing content script injection');
  }
});

async function checkBackendHealth() {
  try {
    const response = await fetch('http://localhost:5000/health', {
      method: 'GET',
      mode: 'cors',
      headers: { 'Content-Type': 'application/json' }
    });
    if (response.ok) {
      const data = await response.json();
      return { success: true, status: 'online', data };
    } else {
      throw new Error(`Backend returned ${response.status}`);
    }
  } catch (error) {
    return { success: false, status: 'offline', error: error.message };
  }
}

let backendCheckInterval;
chrome.storage.local.get(['extensionEnabled'], (result) => {
  if (result.extensionEnabled) {
    startBackendMonitoring();
  }
});

function startBackendMonitoring() {
  if (backendCheckInterval) return;
  backendCheckInterval = setInterval(async () => {
    const health = await checkBackendHealth();
    if (!health.success) {
      console.warn('Backend health check failed:', health.error);
    }
  }, 30000);
}

function stopBackendMonitoring() {
  if (backendCheckInterval) {
    clearInterval(backendCheckInterval);
    backendCheckInterval = null;
  }
}

chrome.storage.onChanged.addListener((changes) => {
  if (changes.extensionEnabled) {
    if (changes.extensionEnabled.newValue) {
      startBackendMonitoring();
    } else {
      stopBackendMonitoring();
    }
  }
});

chrome.runtime.onSuspend.addListener(() => {
  stopBackendMonitoring();
  console.log('Sign Language Translator extension suspended');
});