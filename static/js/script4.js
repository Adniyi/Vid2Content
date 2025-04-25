
document.addEventListener('DOMContentLoaded', () => {
    // DOM elements
    const processBtn = document.getElementById('process-btn');
    const spinner = document.getElementById('spinner');
    const btnText = document.getElementById('btn-text');
    const result = document.getElementById('result');
    const copyBtn = document.getElementById('copy-btn');
    const copyTooltip = document.getElementById('copy-tooltip');
    const inputField = document.getElementById('youtube-link');
    const errorMessage = document.getElementById('error-message');
    const resultContent = document.getElementById('result-content');
    const socketMessage = document.getElementById('socket-message');

    // API endpoint and socket connection
    const API_ENDPOINT = "http://127.0.0.1:5000/transcript";
    const socket = io("http://localhost:5000");

    socket.on("progress", (data) => {
        console.log("[Progress]", data.message);
        // document.getElementById("status").innerText = data.message;
        displayProgress(data.message)
    });

    socket.on("done", (data) => {
        console.log("[DONE]", data);
        // document.getElementById("result-content").innerText = JSON.stringify(data, null, 2);
        // displayProgress(data.message);
        console.log(data);
        // Display result content
        showResult(data.text);
    });

    socket.on("error", (data) => {
        console.error("[ERROR]", data.message);
        // document.getElementById("status").innerText = "❌ " + data.message;
        displayProgress(data.message);
    });


    // Event listener for process button
    processBtn.addEventListener("click", fetchWithTimeout);

    /**
     * Handle video URL submission and process the video
     */
    async function fetchWithTimeout() {
        const youtubeLink = inputField.value.trim();

        // Validate URL input
        if (!youtubeLink) {
            displayError("Please enter a valid video link");
            return;
        }

        // Reset previous errors
        hideError();

        // Show spinner and change button state
        toggleLoadingState(true);

        try {
            // Send request to the server
            const response = await fetch(API_ENDPOINT, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: youtubeLink }),
            });

            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }

            const data = await response.json();
            console.log(data);

            // Handle server error in response
            if (data.error) {
                displayError(data.error);
                result.style.display = "none";
            } else {
                // Display result content
                showResult(data.content);
            }
        } catch (error) {
            console.error('Error processing YouTube link:', error);
            displayError('Error processing video. Please try again.');
        } finally {
            // Hide spinner and restore button state
            toggleLoadingState(false);
        }
    }

    /**
     * Show error message
     * @param {string} message
     */
    function displayError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }

    /**
     * Hide the error message
     */
    function hideError() {
        errorMessage.style.display = 'none';
    }

    /**
     * Toggle the loading state (spinner and button state)
     * @param {boolean} isLoading
     */
    function toggleLoadingState(isLoading) {
        spinner.style.display = isLoading ? 'block' : 'none';
        btnText.textContent = isLoading ? 'Processing...' : 'Process';
        processBtn.disabled = isLoading;
    }

    /**
     * Show the transcription result
     * @param {string} content
     */
    function showResult(content) {
        result.style.display = 'block';
        resultContent.innerHTML = content;
    }

    function displayProgress(message){
        socketMessage.style.display = "block";
        socketMessage.innerText = message;
    }
 
});



