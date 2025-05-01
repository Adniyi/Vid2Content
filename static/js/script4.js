document.addEventListener('DOMContentLoaded', () => {
    // import { marked } from ;
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
    const downloadContainer = document.getElementById('download-container');
    const downlaodHtml = document.getElementById('downloadHmtl');
    const downlaodTxt = document.getElementById('downloadTxt');
    const downloadMd = document.getElementById('downloadMD');
    let raw_markdown = "";
    // API endpoint and socket connection
    const API_ENDPOINT = "http://127.0.0.1:5000/transcript";
    const socket = io("http://localhost:5000");

    socket.on("progress", (data) => {
        console.log("[Progress]", data.message);
        // document.getElementById("status").innerText = data.message;
        displayProgress(data.message)
    });
    
    
    

    // socket.on("error", (data) => {
    //     console.error("[ERROR]", data.message);
    //     // document.getElementById("status").innerText = "❌ " + data.message;
    //     displayProgress(data.message);
    // });


    // Event listener for process button
    processBtn.addEventListener("click", fetchWithTimeout);
    copyBtn.addEventListener('click', copyContent);
    downlaodHtml.addEventListener('click', () => {
        const htmlContent = resultContent.innerHTML;
        downloadContent('transcript.html', htmlContent,'text/html');
    });

    downlaodTxt.addEventListener('click', ()=>{
        const plainContent = resultContent.innerText;
        downloadContent('transcript.txt', plainContent, 'text/plain');
    });

    downloadMd.addEventListener('click', ()=>{
        const markdownContent = raw_markdown;
        downloadContent('transcript.md', markdownContent, 'text/markdown');
    });

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

            const ErrorMessage = response.error;
            if(ErrorMessage){
                showResult(ErrorMessage);
            }
            const reader = response.body.getReader();
            let output = "";
            

            while(true){
                const { done, value } = await reader.read()
                output += new TextDecoder().decode(value)
                showResult(output); 

                if(done){
                    return;
                }
            }


            // console.log(data.combined_keywords);
            // console.log(data.text);

            // Handle server error in response
            if (data.error) {
                displayError(data.error);
                result.style.display = "none";
            } else {
                // Display result content
                showResult(data.text);
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
        raw_markdown = content;
        const html = marked.parse(content);
        result.style.display = 'block';
        resultContent.innerHTML = html;
        downloadContainer.style.display = 'block';
    }

    function displayProgress(message){
        socketMessage.style.display = "block";
        socketMessage.innerText = message;
    }
    
    function copyContent(){
        const content = resultContent.innerHTML;

        if(content.trim() === ""){
            copyTooltip.innerText = "Nothing to copy";
            return;
        }

        navigator.clipboard.writeText(content)
        .then(()=>{
            copyTooltip.style.display = "block";

            setTimeout(()=>{
                copyTooltip.style.display = "none";
            },2000);
        });

    }

    function downloadContent(filename, content, mimetype){
        const blob = new Blob([content], {type: mimetype});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');

        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
});



