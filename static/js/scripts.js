function appendChat(sender, message, messageType = 'not an error') {
    var color;
    var backgroundColor = '';

    if (messageType === 'error') {
        color = 'red';
        backgroundColor = 'rgba(0, 0, 0, 0.1)';
    } else {
        color = sender === 'AI' ? '#4b8c6e' : 'rgba(0, 0, 0, 0.5)';
    }

    var chatBox = document.getElementById('chat-box');
    

    var chatContent = '<p style="color:' + color + '; background-color:' + backgroundColor + '; ' + 'font-weight: bold;' + ' padding: 5px; border-radius: 5px;">' + sender + ': ' + message + '</p>';

    chatBox.innerHTML += chatContent;
    chatBox.scrollTop = chatBox.scrollHeight;
}



function showPapers() {
    return new Promise((resolve, reject) => {
        var userMessage = $("#message-input").val();
        $.ajax({
            url: '/get_papers?msg=' + encodeURIComponent(userMessage), // Assume this endpoint returns the research papers
            type: 'GET',
            success: function(response) {
                
            var paper_num = 1;
            var papers = response.papers; // Adjust this line based on the response structure
            if (papers == 'None'){
                appendChat('AI', 'No Research Papers Found.Please Try with different Query', 'error');
                $("#message-input").val('');
                return;
            }
            var message = '<strong>Research papers Relavent to the given query:</strong><br>';
            papers.forEach(function(paper) {
                message += String(paper_num) + '. ';
                if (paper.url) {
                    message += '<a class="paper-link" href="' + paper.url + '" target="_blank">' + paper.title + '</a>';
                } else {
                    message += paper.title; // If no URL, just add the title
                }
                if (paper.pdf_url && paper.pdf_url !== '') {
                    message += ' [<a class="paper-link" href="' + paper.pdf_url + '" target="_blank">PDF</a>]';
                }
                message += '<br>';
                paper_num++;
            });

            $("#message-input").val('');
            appendChat('AI', message);
                hideLoadingAnimation();
                resolve(); // Resolve the promise when successful
                
            },
            error: function(error) {
                hideLoadingAnimation();
                $("#message-input").val('');
                appendChat('AI', 'No Research Papers Found. Please Try with different Query', 'error');
                reject(error); // Reject the promise if there is an error
            }
        });
    });
}


function addAnchorTagsToURLs(text) {
    const urlRegex = /(\b(https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/ig;
      const anchorText = text.replace(urlRegex, function(url) {
      return '<a href="' + url + '" target="_blank">' + url + '</a>';
    });
  
    return anchorText;
  }



async function showResearchresponse() {
    var userMessage = $("#message-input").val();

    if (!userMessage) {
        appendChat('AI', 'Please enter a message before submitting.', 'error');
        hideLoadingAnimation();
        return; 
    }

    appendChat('You', userMessage);

    try {
        showLoadingAnimation("Searching relevant research papers...");
        await showPapers();
        hideLoadingAnimation();
        showLoadingAnimation("Generating Short Answer...");
        var medsearchResponse = await $.ajax({
            url: '/medsearch?msg=' + encodeURIComponent(userMessage),
            type: 'POST'
        });
        // processMedsearchResponse(medsearchResponse);
        appendChat('AI', medsearchResponse.medsearch);
        hideLoadingAnimation();
        showLoadingAnimation("Generating more comprehensive Answer may take few minutes...");
        var researchResponse = await $.ajax({
            url: '/get_research_answer?msg=' + encodeURIComponent(userMessage),
            type: 'GET'
        });
        appendChat('AI', addAnchorTagsToURLs(researchResponse.research_response));

        hideLoadingAnimation();
    } catch (error) {
        console.error("An error occurred: ", error);
        appendChat('AI', 'An error occurred while fetching responses.', 'error');
    } finally {
        hideLoadingAnimation();
    }
}







$(document).ready(function() {
    var $messageInput = $('#message-input');
    var $sendContainer = $('#send-container');
    appendChat('AI','Hi, How can you help you today?')
    $sendContainer.on('submit', function(e) {
        e.preventDefault();

        var msg = $messageInput.val().trim();
        if (!msg) {
            appendChat('AI', 'Please enter a message before submitting.', 'error');
            hideLoadingAnimation();
            return; // Exit early if no input
        }
        appendChat('You', msg);
        $messageInput.val('');
        showLoadingAnimation("Generating answer from LLM ....");
        $.ajax({

            url: '/get_response',
            data: { 'msg': msg },
            type: 'POST',
            success: function(response) {
                appendChat('AI', response.response);
                hideLoadingAnimation();
            },
            error: function(error) {
                appendChat('AI', "Error Occured.")
                hideLoadingAnimation();
            }
        });
    });
});






function showLoadingAnimation(loadingText) {
    $('#loading-spinner').css('display', 'flex');
    $('#loading-spinner p').html(loadingText);
}

function hideLoadingAnimation() {
    $('#loading-spinner').css('display', 'none');
}





// Text Area
const textarea = document.getElementById('expanding-textarea');
const form = document.getElementById('textarea-form');

textarea.addEventListener('input', function() {
    this.style.height = 'auto'; // Reset height
    this.style.height = (this.scrollHeight) + 'px'; // Set new height
});

textarea.addEventListener('keydown', function(event) {
    if (event.key == 'Enter') {
        event.preventDefault(); // Prevent line break
        form.submit(); // Submit the form
    }
});



$('#toggle-dark-mode').click(function() {
    $('body').toggleClass('dark-mode');
});

