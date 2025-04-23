document.addEventListener('DOMContentLoaded', ()=> {
    const processBtn = document.getElementById('process-btn');
    const spinner = document.getElementById('spinner');
    const btnText = document.getElementById('btn-text');
    const result = document.getElementById('result');
    const copyBtn = document.getElementById('copy-btn');
    const copyTooltip = document.getElementById('copy-tooltip');
    const inputField = document.getElementById('youtube-link');
    const errorMessage = document.getElementById('error-message');



    // const API_ENDPOINT = "http://127.0.0.1:5000/transcript";

    processBtn.addEventListener("click", fetchWithTimeout);

    async function fetchWithTimeout() {
        const youtubeLink = inputField.value.trim();
        // const controller = new AbortController();
        // const timeout = setTimeout(()=> controller.abort(), 5000);

        if(!youtubeLink){
            errorMessage.textContent = "Please enter a valid video link";
            errorMessage.style.display = "block"
        }

        // Hide any previous error message
        errorMessage.style.display = 'none';
        
        // Show spinner and change button text
        spinner.style.display = 'block';
        btnText.textContent = 'Processing...';
        processBtn.disabled = true;
        
        // Hide result if it was visible
        result.style.display = 'none';

        try{
            const request = await fetch("http://127.0.0.1:5000/transcript",{
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({url: youtubeLink}),
                // signal: controller.signal,
            })
            // clearTimeout(timeout);

            if (!request.ok) {
                throw new Error(`Server resonsed with ${request.status}`)
            }

            const data = await request.json();

            // await new Promise(resolve => setTimeout(resolve, 5000));
            console.log(data['error']);

            if(data['error']){
                errorMessage.textContent = data['error'];
                result.style.display = "none";document.addEventListener('DOMContentLoaded', ()=> {
    const processBtn = document.getElementById('process-btn');
    const spinner = document.getElementById('spinner');
    const btnText = document.getElementById('btn-text');
    const result = document.getElementById('result');
    const copyBtn = document.getElementById('copy-btn');
    const copyTooltip = document.getElementById('copy-tooltip');
    const inputField = document.getElementById('youtube-link');
    const errorMessage = document.getElementById('error-message');
    const resultContent = document.getElementById('result-content');

    const API_ENDPOINT = "http://127.0.0.1:5000/transcript";

    processBtn.addEventListener("click", fetchWithTimeout);

    async function fetchWithTimeout() {
        const youtubeLink = inputField.value.trim();

        if(!youtubeLink){
            errorMessage.textContent = "Please enter a valid video link";
            errorMessage.style.display = "block";
            return;
        }

        // Hide any previous error message
        errorMessage.style.display = 'none';
        
        // Show spinner and change button text
        spinner.style.display = 'block';
        btnText.textContent = 'Processing...';
        processBtn.disabled = true;
        
        // Hide result if it was visible
        result.style.display = 'none';

        try{
            const request = await fetch(API_ENDPOINT,{
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({url: youtubeLink}),
            })

            if (!request.ok) {
                throw new Error(`Server responded with ${request.status}`)
            }

            const data = await request.json();
            
            // if the server sends an error or is unable to transcribe the link.
            if(data['error']){
                errorMessage.textContent = data['error'];
                result.style.display = "none";
                errorMessage.style.display = 'block';
            }else{
                // Show result
                result.style.display = 'block';
                resultContent.innerHTML = data.content;
            }
        } catch (error) {
            console.error('Error processing YouTube link:', error);
            errorMessage.textContent = 'Error processing video. Please try again.';
            errorMessage.style.display = 'block';
        } finally {
        // Hide spinner and restore button text
            spinner.style.display = 'none';
            btnText.textContent = 'Process';
            processBtn.disabled = false;
        }
    }
});
                errorMessage.style.display = 'block';
            }else{
                // Show result
                result.style.display = 'block';
            }
            // document.getElementById('result-content').innerHTML +=`${data.content}`
            
        
        } catch (error) {
            console.error('Error processing YouTube link:', error);
            errorMessage.textContent = 'Error processing video. Please try again.';
            errorMessage.style.display = 'block';
        } finally {
        // Hide spinner and restore button text
            spinner.style.display = 'none';
            btnText.textContent = 'Process';
            processBtn.disabled = false;
        }
    }
});