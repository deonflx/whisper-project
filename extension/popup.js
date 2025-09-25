document.addEventListener('DOMContentLoaded', async () => {
  const toggleButton = document.getElementById('toggle-button');
  const extensionStatus = document.getElementById('extension-status');
  const videoStatus = document.getElementById('video-status');
  const subtitleStatus = document.getElementById('subtitle-status');
  const backendStatus = document.getElementById('backend-status');
  
  let isActive = false;
  let currentTab = null;
  
  // Check backend status on startup
  await checkBackendStatus();
  
  // Initialize extension
  await initializeExtension();
  
  async function initializeExtension() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      currentTab = tab;
      
      // Skip chrome pages
      if (!tab.url || tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://')) {
        updateUI({ 
          active: false, 
          hasVideo: false, 
          hasSubtitles: false, 
          error: 'Not a web page. Please navigate to a video website.' 
        });
        return;
      }
      
      console.log('Initializing on tab:', tab.url);
      
      // Inject content script
      await injectContentScript();
      
      // Wait for initialization
      await new Promise(resolve => setTimeout(resolve, 800));
      
      // Get initial status
      await getStatus();
      
    } catch (error) {
      console.error('Initialization error:', error);
      updateUI({ 
        active: false, 
        hasVideo: false, 
        hasSubtitles: false, 
        error: 'Failed to initialize. Please refresh the page.' 
      });
    }
  }
  
  async function injectContentScript() {
    try {
      // Inject CSS
      await chrome.scripting.insertCSS({
        target: { tabId: currentTab.id },
        files: ['content.css']
      });
      
      // Inject JavaScript
      await chrome.scripting.executeScript({
        target: { tabId: currentTab.id },
        files: ['content.js']
      });
      
      console.log('Content script injected successfully');
    } catch (error) {
      console.error('Failed to inject content script:', error);
      throw new Error('Could not inject content script. Please refresh the page.');
    }
  }
  
  async function getStatus() {
    try {
      const response = await chrome.tabs.sendMessage(currentTab.id, { 
        action: 'getStatus' 
      });
      console.log('Status response:', response);
      updateUI(response);
    } catch (error) {
      console.log('No response from content script, attempting reinject...');
      try {
        await injectContentScript();
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        const response = await chrome.tabs.sendMessage(currentTab.id, { 
          action: 'getStatus' 
        });
        updateUI(response);
      } catch (retryError) {
        console.error('Retry failed:', retryError);
        updateUI({ 
          active: false, 
          hasVideo: false, 
          hasSubtitles: false, 
          error: 'Content script not responding. Please refresh the page.' 
        });
      }
    }
  }
  
  toggleButton.addEventListener('click', async () => {
    if (!currentTab || !currentTab.url || currentTab.url.startsWith('chrome://')) {
      alert('Please navigate to a video website first.');
      return;
    }
    
    // Disable button temporarily
    toggleButton.disabled = true;
    
    isActive = !isActive;
    
    try {
      const response = await chrome.tabs.sendMessage(currentTab.id, { 
        action: 'toggleExtension', 
        active: isActive 
      });
      
      console.log('Toggle response:', response);
      
      if (response && response.success) {
        updateToggleButton(isActive);
        extensionStatus.textContent = isActive ? 'Active' : 'Inactive';
        extensionStatus.className = `status-indicator ${isActive ? 'status-active' : 'status-inactive'}`;
        
        // Refresh status after toggle
        setTimeout(getStatus, 500);
      } else {
        console.error('Toggle failed');
        isActive = !isActive; // Revert
        alert('Failed to toggle extension. Please try refreshing the page.');
      }
      
    } catch (error) {
      console.error('Error toggling extension:', error);
      isActive = !isActive; // Revert
      
      // Try to reinject and toggle again
      try {
        await injectContentScript();
        await new Promise(resolve => setTimeout(resolve, 500));
        
        const response = await chrome.tabs.sendMessage(currentTab.id, { 
          action: 'toggleExtension', 
          active: isActive 
        });
        
        if (response && response.success) {
          updateToggleButton(isActive);
          extensionStatus.textContent = isActive ? 'Active' : 'Inactive';
          extensionStatus.className = `status-indicator ${isActive ? 'status-active' : 'status-inactive'}`;
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
      extensionStatus.className = 'status-indicator status-inactive';
      videoStatus.textContent = 'Unknown';
      videoStatus.className = 'status-indicator status-unknown';
      subtitleStatus.textContent = 'Unknown';
      subtitleStatus.className = 'status-indicator status-unknown';
      
      // Show error in backend status temporarily
      const originalText = backendStatus.textContent;
      const originalClass = backendStatus.className;
      backendStatus.textContent = status.error;
      backendStatus.className = 'backend-status backend-offline';
      
      setTimeout(() => {
        backendStatus.textContent = originalText;
        backendStatus.className = originalClass;
      }, 3000);
      
      return;
    }
    
    isActive = status.active || false;
    
    // Update extension status
    extensionStatus.textContent = status.active ? 'Active' : 'Inactive';
    extensionStatus.className = `status-indicator ${status.active ? 'status-active' : 'status-inactive'}`;
    
    // Update video status
    videoStatus.textContent = status.hasVideo ? 'Found' : 'Not Found';
    videoStatus.className = `status-indicator ${status.hasVideo ? 'status-active' : 'status-inactive'}`;
    
    // Update subtitle status
    subtitleStatus.textContent = status.hasSubtitles ? 'Available' : 'Searching...';
    subtitleStatus.className = `status-indicator ${status.hasSubtitles ? 'status-active' : 'status-unknown'}`;
    
    updateToggleButton(status.active || false);
  }
  
  function updateToggleButton(active) {
    if (active) {
      toggleButton.textContent = 'Stop Translation';
      toggleButton.className = 'toggle-button active';
    } else {
      toggleButton.textContent = 'Start Translation';
      toggleButton.className = 'toggle-button inactive';
    }
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
        const data = await response.json();
        backendStatus.textContent = 'Flask Backend: Connected ✓';
        backendStatus.className = 'backend-status backend-online';
      } else {
        throw new Error('Backend not responding properly');
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        backendStatus.textContent = 'Flask Backend: Connection Timeout';
      } else {
        backendStatus.textContent = 'Flask Backend: Offline (Start Flask server on port 5000)';
      }
      backendStatus.className = 'backend-status backend-offline';
    }
  }
  
  // Refresh backend status every 10 seconds
  setInterval(checkBackendStatus, 10000);
  
  // Refresh extension status every 5 seconds
  setInterval(async () => {
    if (currentTab && currentTab.url && !currentTab.url.startsWith('chrome://')) {
      try {
        await getStatus();
      } catch (error) {
        // Ignore periodic check errors - they'll be handled in getStatus
      }
    }
  }, 5000);
});