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
    const saveBtn = document.getElementById('save-btn');
    let raw_markdown = "";
    // API endpoint and socket connection
    const API_ENDPOINT = "https://4d31-102-91-105-145.ngrok-free.app/transcript";
    const socket = io("https://4d31-102-91-105-145.ngrok-free.app");

    socket.on("progress", (data) => {
        console.log("[Progress]", data.message);
        // document.getElementById("status").innerText = data.message;
        displayProgress(data.message)
    });
    
    


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
                body: JSON.stringify({ 
                    url: youtubeLink ,
                    user_id: USER_ID,  // Expose this from Flask: const USER_ID = "{{ current_user.id }}";
                }),
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

            const transcriptionId = response.headers.get("X-Transcription-ID");
            console.log("Transcription ID:", transcriptionId); 
            

            while(true){
                const { done, value } = await reader.read()
                output += new TextDecoder().decode(value)
                showResult(output); 

                if(done){
                    saveBtn.disabled = false
                    saveBtn.addEventListener('click', async ()=>{
                        const content = raw_markdown;
                        if(!transcriptionId) return alert("Missing transcrition ID");

                        const response = await fetch("/save_article",{
                            method: 'POST',
                            headers:{'Content-Type': 'application/json'},
                            body:JSON.stringify({
                                user_id:USER_ID,
                                transcription_id:transcriptionId,
                                content:content
                            })
                        });
                        const data = await response.json()
                        if (data.success) {
                            alert("Article saved Successfully");
                            downloadContainer.style.display = 'block';
                        }else{
                            alert("Failed to save article");
                        }
                    });

                    return;
                }

                
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



