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
        showLoadingAnimation("Searching For Research Papers....");
        $.ajax({
            url: '/get_papers?msg=' + encodeURIComponent(userMessage), // Assume this endpoint returns the research papers
            type: 'GET',
            success: function(response) {
                
            var paper_num = 1;
            var papers = response.papers; // Adjust this line based on the response structure
            if (papers == 'None'){
                appendChat('AI', 'No Research Papers Found.Please Try with different Query', 'error');
                hideLoadingAnimation();
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
            message = '<strong>' + message + '</strong>'
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

async function showResearchresponse() {
    var userMessage = $("#message-input").val();
    
    if (!userMessage) {
        appendChat('AI', 'Please enter a message before submitting.', 'error');
        hideLoadingAnimation();
        return; // Exit early if no input
    }
    
    appendChat('You', userMessage)
    showLoadingAnimation();
    try {
        await showPapers(); // Wait for showPapers to complete
        showLoadingAnimation();
        $.ajax({
            url: '/get_research_answer?msg=' + encodeURIComponent(userMessage), // Endpoint to get the research answer
            type: 'GET',
            success: function(response) {
                hideLoadingAnimation();
                var researchResponse = response.research_response;
            // Replace URL references with actual links
            researchResponse = researchResponse.replace(/\[\[(\d+)\]\(URL\)\]/g, function(match, number) {
                return '<a href="URL_OF_PAPER_' + number + '" target="_blank">[' + number + ']</a>';
            });
            var urlRegex = /https?:\/\/[^\s]+/g;
            researchResponse = researchResponse.replace(urlRegex, function(url) {
            return '<a href="' + url + '" target=_blank">' + url + '</a>';
                });
            appendChat('AI', researchResponse);
            },
            error: function(error) {
                appendChat('AI', 'Error While fetching response', 'error');
                hideLoadingAnimation();
            }
        });
    } catch (error) {
        appendChat('AI', 'An error occurred while showing papers.', 'error');
        
        hideLoadingAnimation();
    }
}



$(document).ready(function() {
    var $messageInput = $('#message-input');
    var $sendContainer = $('#send-container');

    $sendContainer.on('submit', function(e) {
        e.preventDefault();
        showLoadingAnimation();

        var msg = $messageInput.val().trim();
        if (!msg) {
            appendChat('AI', 'Please enter a message before submitting.', 'error');
            hideLoadingAnimation();
            return; // Exit early if no input
        }
        appendChat('You', msg);
        $messageInput.val('');

        $.ajax({
            url: '/get_response',
            data: { 'msg': msg },
            type: 'POST',
            success: function(response) {
                $('.loading-spinner').css('display', 'none');
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


function medsearch(userMessage) {
    showLoadingAnimation();
    try {
        $.ajax({
            url: '/medsearch?msg=' + encodeURIComponent(userMessage), // Endpoint to call medsearch
            type: 'POST',
            success: function(response) {
                hideLoadingAnimation();
                var medsearchResponse = response.medsearch;
                // Replace URL references with actual links, if needed
                medsearchResponse = medsearchResponse.replace(/\[\[(\d+)\]\(URL\)\]/g, function(match, number) {
                    return '<a href="URL_OF_PAPER_' + number + '" target=_blank">[' + number + ']</a>';
                });
                $("#message-input").val('');
                appendChat('AI', medsearchResponse);
            },
            error: function(error) {
                console.log(error);
                appendChat('AI', 'Error While fetching response', 'error');
                hideLoadingAnimation();
            }
        });
    } catch (error) {
        console.log(error);
        $("#message-input").val('');
        appendChat('AI', 'An error occurred while executing the medsearch.', 'error');
        hideLoadingAnimation();
    }
}



function showLoadingAnimation(loadingText) {
    $('#loading-spinner').css('display', 'inline-block');
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

