document.addEventListener("DOMContentLoaded", () => {
  chrome.storage.local.get("lastWord", ({ lastWord }) => {
    if (lastWord) {
      document.getElementById("word").value = lastWord;
    }
  });

  document.getElementById("send").addEventListener("click", () => {
    const word = document.getElementById("word").value;
    const tags = document.getElementById("tags").value;

    // Send word to your public Streamlit app
    fetch("https://your-fieldbook.streamlit.app/add_word_api", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ word, tags })
    })
      .then(resp => resp.text())
      .then(msg => {
        document.getElementById("status").textContent = "✅ Word added!";
      })
      .catch(err => {
        document.getElementById("status").textContent = "❌ Failed to add.";
      });
  });
});
