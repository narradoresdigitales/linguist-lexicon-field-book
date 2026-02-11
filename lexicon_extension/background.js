chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "add-to-lexicon",
    title: "Add '%s' to Lexicon",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "add-to-lexicon" && info.selectionText) {
    // Save to local storage temporarily
    chrome.storage.local.set({ lastWord: info.selectionText });
    
    // Open popup (optional)
    chrome.action.openPopup();
  }
});
