document.addEventListener('DOMContentLoaded', async () => {
  const toggleButton = document.getElementById('toggle-button');
  const extensionStatus = document.getElementById('extension-status');
  const videoStatus = document.getElementById('video-status');
  const subtitleStatus = document.getElementById('subtitle-status');
  const backendStatus = document.getElementById('backend-status');
  let isActive = false;
  let currentTab = null;

  await checkBackendStatus();
  await initializeExtension();

  async function initializeExtension() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      currentTab = tab;
      if (!tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://')) {
        updateUI({ active: false, hasVideo: false, hasSubtitles: false, error: 'Not a web page. Please navigate to a video website.' });
        return;
      }
      console.log('Initializing on tab:', tab.url);
      await injectContentScript();
      await new Promise(resolve => setTimeout(resolve, 800));
      await getStatus();
    } catch (error) {
      console.error('Initialization error:', error);
      updateUI({ active: false, hasVideo: false, hasSubtitles: false, error: 'Failed to initialize. Please refresh the page.' });
    }
  }

  async function injectContentScript() {
    try {
      await chrome.scripting.insertCSS({ target: { tabId: currentTab.id }, files: ['content.css'] });
      await chrome.scripting.executeScript({ target: { tabId: currentTab.id }, files: ['content.js'] });
      console.log('Content script injected successfully');
    } catch (error) {
      console.error('Failed to inject content script:', error);
      throw new Error('Could not inject content script. Please refresh the page.');
    }
  }

  async function getStatus() {
    try {
      const response = await chrome.tabs.sendMessage(currentTab.id, { action: 'getStatus' });
      console.log('Status response:', response);
      updateUI(response);
    } catch (error) {
      console.log('No response from content script, attempting reinject...');
      try {
        await injectContentScript();
        await new Promise(resolve => setTimeout(resolve, 1000));
        const response = await chrome.tabs.sendMessage(currentTab.id, { action: 'getStatus' });
        updateUI(response);
      } catch (retryError) {
        console.error('Retry failed:', retryError);
        updateUI({ active: false, hasVideo: false, hasSubtitles: false, error: 'Content script not responding. Please refresh the page.' });
      }
    }
  }

  toggleButton.addEventListener('click', async () => {
    if (!currentTab || !currentTab.url || currentTab.url.startsWith('chrome://')) {
      alert('Please navigate to a video website first.');
      return;
    }
    toggleButton.disabled = true;
    isActive = !isActive;
    try {
      const response = await chrome.tabs.sendMessage(currentTab.id, { action: 'toggleExtension', active: isActive });
      console.log('Toggle response:', response);
      if (response && response.success) {
        updateToggleButton(isActive);
        extensionStatus.textContent = isActive ? 'Active' : 'Inactive';
        extensionStatus.className = isActive ? 'status-active' : 'status-inactive';
        setTimeout(getStatus, 500);
      } else {
        console.error('Toggle failed');
        isActive = !isActive;
        alert('Failed to toggle extension. Please try refreshing the page.');
      }
    } catch (error) {
      console.error('Error toggling extension:', error);
      isActive = !isActive;
      try {
        await injectContentScript();
        await new Promise(resolve => setTimeout(resolve, 500));
        const response = await chrome.tabs.sendMessage(currentTab.id, { action: 'toggleExtension', active: isActive });
        if (response && response.success) {
          updateToggleButton(isActive);
          extensionStatus.textContent = isActive ? 'Active' : 'Inactive';
          extensionStatus.className = isActive ? 'status-active' : 'status-inactive';
        } else {
          alert('Could not start extension. Please refresh the page and try again.');
        }
      } catch (retryError) {
        console.error('Retry toggle failed:', retryError);
        alert('Extension error. Please refresh the page and try again.');
      }
    } finally {
      toggleButton.disabled = false;
    }
  });

  function updateUI(status) {
    console.log('Updating UI with status:', status);
    if (status.error) {
      extensionStatus.textContent = 'Error';
      extensionStatus.className = 'status-inactive';
      videoStatus.textContent = 'Unknown';
      videoStatus.className = 'status-unknown';
      subtitleStatus.textContent = 'Unknown';
      subtitleStatus.className = 'status-unknown';
      backendStatus.textContent = status.error;
      backendStatus.className = 'backend-offline';
      setTimeout(checkBackendStatus, 3000);
      return;
    }
    isActive = status.active || false;
    extensionStatus.textContent = status.active ? 'Active' : 'Inactive';
    extensionStatus.className = status.active ? 'status-active' : 'status-inactive';
    videoStatus.textContent = status.hasVideo ? 'Found' : 'Not Found';
    videoStatus.className = status.hasVideo ? 'status-active' : 'status-inactive';
    subtitleStatus.textContent = status.hasSubtitles ? 'Available' : 'Searching...';
    subtitleStatus.className = status.hasSubtitles ? 'status-active' : 'status-unknown';
    updateToggleButton(status.active || false);
  }

  function updateToggleButton(active) {
    toggleButton.textContent = active ? 'Stop Translation' : 'Start Translation';
    toggleButton.classList.toggle('active', active);
  }

  async function checkBackendStatus() {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);
      const response = await fetch('http://localhost:5000/health', {
        method: 'GET',
        mode: 'cors',
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      if (response.ok) {
        backendStatus.textContent = 'Flask Backend: Connected ✓';
        backendStatus.className = 'backend-online';
      } else {
        throw new Error('Backend not responding properly');
      }
    } catch (error) {
      backendStatus.textContent = error.name === 'AbortError' ? 'Flask Backend: Connection Timeout' : 'Flask Backend: Offline (Start Flask server on port 5000)';
      backendStatus.className = 'backend-offline';
    }
  }

  setInterval(checkBackendStatus, 10000);
  setInterval(async () => {
    if (currentTab && currentTab.url && !currentTab.url.startsWith('chrome://')) {
      try {
        await getStatus();
      } catch (error) {}
    }
  }, 5000);
});