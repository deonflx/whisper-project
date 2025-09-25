(function() {
  'use strict';
  
  let currentVideo = null;
  let signTokensData = [];
  let signGifOverlay = null;
  let isExtensionActive = false;
  let currentGifTimeout = null;
  let initialized = false;
  let currentTokenIndex = 0;

  const gifPaths = {
    'HELLO': 'gifs/hello.gif',
    'WORLD': 'gifs/world.gif',
    'HOW': 'gifs/how.gif',
    'YOU': 'gifs/you.gif',
    'DO': 'gifs/do.gif',
    'I': 'gifs/i.gif',
    'AM': 'gifs/am.gif',
    'FINE': 'gifs/fine.gif',
    'THANK': 'gifs/thank.gif',
    'GOOD': 'gifs/good.gif',
    'BAD': 'gifs/bad.gif',
    'YES': 'gifs/yes.gif',
    'NO': 'gifs/no.gif',
    'PLEASE': 'gifs/please.gif',
    'SORRY': 'gifs/sorry.gif',
    'TRAVEL': 'gifs/travel.gif',
    'VIDEO': 'gifs/video.gif',
    'MINUTE': 'gifs/minute.gif',
    'HOME': 'gifs/home.gif',
    'DRONE': 'gifs/drone.gif',
    'CAMERA': 'gifs/camera.gif',
    'BOOK': 'gifs/book.gif',
    'PAGE': 'gifs/page.gif',
    'DAY': 'gifs/day.gif',
    'FUN': 'gifs/fun.gif',
    'IDEA': 'gifs/idea.gif',
    'LOVE': 'gifs/love.gif',
    'WITH': 'gifs/hello.gif',
    'GET': 'gifs/you.gif'
};

  initialize();

  function initialize() {
    if (initialized) return;
    initialized = true;
    console.log('Sign Language Extension: Content script initializing...');
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initializeExtension);
    } else {
      initializeExtension();
    }
    window.addEventListener('load', initializeExtension);
  }

  function initializeExtension() {
    console.log('Sign Language Extension: DOM ready, finding videos...');
    findVideoElements();
    const observer = new MutationObserver((mutations) => {
      let shouldCheck = false;
      mutations.forEach(mutation => {
        if (mutation.type === 'childList') {
          mutation.addedNodes.forEach(node => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              if (node.tagName === 'VIDEO' || node.querySelector('video')) {
                shouldCheck = true;
              }
            }
          });
        }
      });
      if (shouldCheck && !currentVideo) {
        setTimeout(findVideoElements, 500);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    console.log('Sign Language Extension: Content script ready');
  }

  function findVideoElements() {
    const videos = document.querySelectorAll('video');
    console.log(`Sign Language Extension: Found ${videos.length} video elements`);
    if (videos.length > 0) {
      let selectedVideo = null;
      for (let video of videos) {
        if (!video.paused || video.currentTime > 0) {
          selectedVideo = video;
          break;
        }
      }
      if (!selectedVideo) {
        selectedVideo = Array.from(videos).reduce((largest, video) => {
          const currentSize = video.videoWidth * video.videoHeight;
          const largestSize = largest ? largest.videoWidth * largest.videoHeight : 0;
          return currentSize > largestSize ? video : largest;
        }, videos[0]);
      }
      if (selectedVideo !== currentVideo) {
        currentVideo = selectedVideo;
        console.log('Sign Language Extension: Video selected');
        setupVideoListeners();
        setTimeout(extractSubtitles, 1000);
      }
    } else {
      currentVideo = null;
      console.log('Sign Language Extension: No videos found on page');
    }
  }

  function setupVideoListeners() {
    if (!currentVideo) return;
    currentVideo.addEventListener('timeupdate', handleTimeUpdate);
    currentVideo.addEventListener('play', handleVideoPlay);
    currentVideo.addEventListener('pause', handleVideoPause);
    currentVideo.addEventListener('seeked', handleVideoSeeked);
  }

  function handleTimeUpdate() {
    if (!isExtensionActive || !signTokensData.length) return;
    const currentTime = currentVideo.currentTime;
    const activeTokenGroup = findActiveTokenGroup(currentTime);
    if (activeTokenGroup) {
      displaySignGifs(activeTokenGroup.tokens);
    } else {
      hideSignGifs();
    }
  }

  function handleVideoPlay() {
    if (isExtensionActive && signGifOverlay) {
      signGifOverlay.style.display = 'block';
    }
  }

  function handleVideoPause() {
    if (signGifOverlay) {
      signGifOverlay.style.display = 'none';
    }
  }

  function handleVideoSeeked() {
    if (currentGifTimeout) {
      clearTimeout(currentGifTimeout);
    }
  }

  function findActiveTokenGroup(currentTime) {
    return signTokensData.find(tokenGroup => 
      currentTime >= tokenGroup.start && currentTime <= tokenGroup.end
    );
  }

  function extractSubtitles() {
    let subtitles = [];
    const textTracks = currentVideo.textTracks;
    if (textTracks.length > 0) {
      for (let i = 0; i < textTracks.length; i++) {
        const track = textTracks[i];
        if (track.kind === 'subtitles' || track.kind === 'captions') {
          subtitles = extractFromTextTrack(track);
          break;
        }
      }
    }
    if (subtitles.length === 0) {
      subtitles = extractFromDOMSubtitles();
    }
    if (subtitles.length > 0) {
      console.log('Extracted subtitles:', subtitles);
      sendSubtitlesToBackend(subtitles);
    } else {
      console.log('No subtitles found');
      handleNoSubtitles();
    }
  }

  function extractFromTextTrack(track) {
    const subtitles = [];
    try {
      track.mode = 'showing';
      const cues = track.cues;
      if (cues) {
        for (let i = 0; i < cues.length; i++) {
          const cue = cues[i];
          subtitles.push({
            start: cue.startTime,
            end: cue.endTime,
            text: cue.text.replace(/<[^>]*>/g, '')
          });
        }
      }
    } catch (error) {
      console.log('Error extracting from text track:', error);
    }
    return subtitles;
  }

  function extractFromDOMSubtitles() {
    const subtitles = [];
    const ytCaptions = document.querySelectorAll('.ytp-caption-segment');
    if (ytCaptions.length > 0) {
      ytCaptions.forEach((caption, index) => {
        subtitles.push({
          start: index * 2,
          end: (index + 1) * 2,
          text: caption.textContent.trim()
        });
      });
    }
    const netflixCaptions = document.querySelectorAll('.player-timedtext-text-container');
    if (netflixCaptions.length > 0) {
      netflixCaptions.forEach((caption, index) => {
        subtitles.push({
          start: index * 3,
          end: (index + 1) * 3,
          text: caption.textContent.trim()
        });
      });
    }
    return subtitles;
  }

  async function sendSubtitlesToBackend(subtitles) {
    try {
      console.log('Sending subtitles to Flask backend...');
      const response = await fetch('http://localhost:5000/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subtitles })
      });
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.signTokens) {
          signTokensData = data.signTokens;
          console.log('Received sign tokens:', signTokensData);
        } else {
          console.error('Backend returned error:', data);
          handleNoSubtitles();
        }
      } else {
        console.error('Backend error:', response.statusText);
        handleNoSubtitles();
      }
    } catch (error) {
      console.error('Error connecting to backend:', error);
      handleNoSubtitles();
    }
  }

  async function sendToTranscribe() {
    try {
      console.log('Sending YouTube URL to Flask backend for transcription...');
      const response = await fetch('http://localhost:5000/transcribe-youtube', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ youtube_url: window.location.href })
      });
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.signTokens) {
          signTokensData = data.signTokens;
          console.log('Received sign tokens from transcription:', signTokensData);
        } else {
          console.error('Backend returned error:', data);
          createDummySignData();
        }
      } else {
        console.error('Backend error:', response.statusText);
        createDummySignData();
      }
    } catch (error) {
      console.error('Error connecting to backend:', error);
      createDummySignData();
    }
  }

  function handleNoSubtitles() {
    if (window.location.href.includes('youtube.com')) {
      console.log('No subtitles found, attempting transcription for YouTube');
      sendToTranscribe();
    } else {
      createDummySignData();
    }
  }

  function createDummySignData() {
    signTokensData = [
      { start: 0.0, end: 3.0, tokens: ["HELLO", "WORLD"] },
      { start: 3.5, end: 6.0, tokens: ["HOW", "YOU"] },
      { start: 6.5, end: 9.0, tokens: ["I", "AM", "FINE"] },
      { start: 9.5, end: 12.0, tokens: ["THANK", "YOU"] }
    ];
    console.log('Using dummy sign data');
  }

  function createSignGifOverlay() {
    if (signGifOverlay) return;
    signGifOverlay = document.createElement('div');
    signGifOverlay.id = 'sign-language-overlay';
    signGifOverlay.innerHTML = `
      <div id="sign-gif-container">
        <img id="sign-gif" src="" alt="Sign language" />
        <div id="sign-text"></div>
      </div>
    `;
    document.body.appendChild(signGifOverlay);
  }

  function displaySignGifs(tokens) {
    if (!signGifOverlay) createSignGifOverlay();
    if (!tokens || tokens.length === 0) {
      hideSignGifs();
      return;
    }
    const gifContainer = document.getElementById('sign-gif-container');
    const signGif = document.getElementById('sign-gif');
    const signText = document.getElementById('sign-text');
    if (currentGifTimeout) clearTimeout(currentGifTimeout);
    signGifOverlay.style.display = 'block';
    gifContainer.style.display = 'block';
    currentTokenIndex = 0;
    showToken(tokens, signGif, signText);
  }

  function showToken(tokens, signGif, signText) {
    if (currentTokenIndex >= tokens.length) {
      currentTokenIndex = 0;
      hideSignGifs();
      return;
    }
    const token = tokens[currentTokenIndex];
    const gifPath = gifPaths[token.toUpperCase()];
    if (gifPath) {
      const fullGifPath = chrome.runtime.getURL(gifPath);
      signGif.src = fullGifPath;
      signGif.style.display = 'block';
      signText.textContent = token;
      currentGifTimeout = setTimeout(() => {
        currentTokenIndex++;
        showToken(tokens, signGif, signText);
      }, 1500);
    } else {
      signText.textContent = token + " (No GIF)";
      signGif.style.display = 'none';
      currentGifTimeout = setTimeout(() => {
        currentTokenIndex++;
        showToken(tokens, signGif, signText);
      }, 1000);
    }
  }

  function hideSignGifs() {
    if (signGifOverlay) {
      const gifContainer = document.getElementById('sign-gif-container');
      if (gifContainer) gifContainer.style.display = 'none';
    }
    if (currentGifTimeout) {
      clearTimeout(currentGifTimeout);
      currentGifTimeout = null;
    }
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('Sign Language Extension: Received message:', message);
    if (message.action === 'ping') {
      sendResponse('pong');
      return true;
    }
    if (message.action === 'toggleExtension') {
      isExtensionActive = message.active;
      console.log('Extension toggled:', isExtensionActive);
      if (isExtensionActive) {
        if (signTokensData.length === 0 && currentVideo) {
          extractSubtitles();
        }
        createSignGifOverlay();
      } else {
        hideSignGifs();
      }
      sendResponse({ success: true, active: isExtensionActive });
      return true;
    }
    if (message.action === 'getStatus') {
      const status = {
        active: isExtensionActive,
        hasVideo: !!currentVideo,
        hasSubtitles: signTokensData.length > 0,
        videoInfo: currentVideo ? {
          duration: currentVideo.duration,
          currentTime: currentVideo.currentTime,
          paused: currentVideo.paused
        } : null
      };
      console.log('Sending status:', status);
      sendResponse(status);
      return true;
    }
    return true;
  });

  document.addEventListener('play', (e) => {
    if (e.target.tagName === 'VIDEO') {
      console.log('Video play event detected');
      if (!currentVideo || e.target !== currentVideo) {
        currentVideo = e.target;
        setupVideoListeners();
      }
      if (isExtensionActive && signTokensData.length === 0) {
        setTimeout(extractSubtitles, 500);
      }
    }
  }, true);

  window.addEventListener('beforeunload', () => {
    if (signGifOverlay) signGifOverlay.remove();
  });

  setInterval(() => {
    if (!currentVideo) findVideoElements();
  }, 2000);

  console.log('Sign Language Extension: Content script loaded');
})(); 