chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'seekTo' && request.time !== undefined) {
    const videoElement = document.querySelector('video');
    if (videoElement) {
      videoElement.currentTime = request.time;
      videoElement.play();
      sendResponse({ status: 'success' });
    } else {
      sendResponse({ status: 'error', message: 'No video element found' });
    }
  }
  return true;
});
