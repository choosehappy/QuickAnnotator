////////////////////////////////////////////////////////////////////////////////////////////////////
// this will contain all the notification messages to display in the notification log:
var notifications = [];

// this hashmap will contain the last line number we have received data about for running jobs:
var running_jobs_line_number = {};
var latest_jobs_error_message = {}; // <-- to avoid duplicate messages
var running_jobs_being_checked = new Set();  // <-- for various job_id's
var running_jobs_command_names = {};
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * Extract the command name for a given job,
 * or output false if the job cannot be found.
 */
function getCommandName(job_id) {

    const table_name = 'job';
    const col_name = 'id';
    const operation = '==';
    const value = job_id;

    const query_results = getDatabaseQueryResults(table_name, col_name, operation, value);

    if (query_results.status != 200) {
        alert('Server error ' + query_results.status + ' when trying to get the command name for job ' + job_id);
        return;
    } else if (!query_results.data.num_results) {
        addNotification('No job found for job ' + job_id);
        return false;
    }
    else {
        return query_results.data.objects[0].cmd;
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * This will populate the notifications with recent messages
 * from a given job and return the number of new lines
 * of output it processed.
 *
 * It will also internally store the latest line number
 * for subsequent calls.
 *
 * It will also only show a popup error message if the error
 * message has changed since last time to avoid repeated popups.
 *
 */
function updateJobNotifications(job_id) {

  // get the latest notifications:
  const line_number = (job_id in running_jobs_line_number) ? running_jobs_line_number[job_id] : 0;
  notifications_output = get_job_notifications(job_id, line_number);
  status_code = notifications_output.status;
  new_job_notifications = notifications_output.data;

  // extract the data:
  let messages = new_job_notifications.objects;
  let count = new_job_notifications.num_results;
  running_jobs_line_number[job_id] = (count == 0 ? 0 : messages[count-1].id);

  // extract the command name (or use cached one)
  const command_name = (job_id in running_jobs_command_names) ?
    running_jobs_command_names[job_id] : getCommandName(job_id);
  running_jobs_command_names[job_id] = command_name;

  // nested function to process the new messages:
  function process_messages(what_to_call, keywords){
    // loop through:
    for (let i = 0; i < count; i++) {
      // parse:
      let message = messages[i].procout;
      for (let j = 0; j < keywords.length; j++) {
        keyword = keywords[j];
        useful_message_position = message.search(keyword);
        if (useful_message_position != -1) {
          let timestamp = messages[i].timestamp;
          let notification = '[' + command_name + ' ' + timestamp + '] ' + message.substring(useful_message_position + keyword.length);
          what_to_call(notification);
        } // if
      } // for j
    } // for i
  } // process_messages

  // add all appropriate notifications to the message pane:
  notification_keywords = ["PROGRESS: ", "USER: ", "ERROR: "];
  process_messages(addNotification, notification_keywords);

  // display any error messages to the user in a popup message:
  //alert_keywords = ["ERROR: "];
  //process_messages(showWindowMessage, alert_keywords);

  // display errors:
  if (status_code != 200) {
    error = 'Error ' + status_code + ': ' + new_job_notifications.error;
    if (latest_jobs_error_message[job_id] != error) {
      showWindowMessage(error);
      latest_jobs_error_message[job_id] = error;
    }
  } // status code

  return count

} // updateJobNotifications
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * This will add a new notification message to the collection.
 *
 * It assumes there is a textarea element with id latest_notification.
 */
function addNotification(message) {
  // add it to the array:
  message = getCurrentTime() + " " + message;
  notifications.push(message);
  // update the latest notification:
  text_area = document.getElementById('notifications');
  text_area.value = get_notifications_as_text();
  text_area.scrollTop = text_area.scrollHeight; // <-- autoscroll to bottom
} // addNotification

/**
 * This will output all the notifications
 * for input in a text area.
 */
function get_notifications_as_text() {
  text = "Notifications:";
  number_of_notifications = notifications.length;
  for (i = 0; i < number_of_notifications; i++) {
    text += "\n";
    text += notifications[i];
  }
  return text;
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * This will repeatedly loop until a given status of a job_id
 * is "DONE" or "ERROR". If it's done, it will call the callback.
 *
 * retry_seconds is the number of seconds between polling the database.
 */
function jobChecker(job_id, completed_callback_function, retry_seconds, command_name, indicationTarget="") {

    const command_string = command_name + ' (job ' + job_id + ')';

    if (updateJobNotifications(job_id) == 0) {
        addNotification('No updates from the server on ' + command_string);
    }

    const job_status = get_job_status(job_id);
    if (job_status == 'QUEUE' || job_status == 'RUNNING') {
        setTimeout(jobChecker.bind(null,
            job_id, completed_callback_function, retry_seconds, command_name, indicationTarget),
            1000 * retry_seconds);
    }
    else {
        running_jobs_being_checked.delete(job_id);
        if (job_status == 'ERROR') {
            showWindowMessage('ERROR: ' + command_string + ' failed.');
            try {
                updateTrafficLight(indicationTarget, colorNOTAVAILABLE)
            } catch (e) {
            }
        } else if (job_status == 'DONE') {
            addNotification('COMPLETED: ' + command_name + ' finished successfully');
            completed_callback_function();
            try {
                updateTrafficLight(indicationTarget, colorAVAILABLE)
            } catch (e) {
            }
        } else {
            showWindowMessage('ERROR: Unexpected job status ' +
                job_status + ' detected for ' + command_string);
            try {
                updateTrafficLight(indicationTarget, colorNOTAVAILABLE)
            } catch (e) {
            }
        }
    }
}

/**
 * Call this function to start a job checker loop
 * which will continuously check on the job and run
 * a callback function when the job is in the "DONE" state.
 *
 * This is useful when creating a new job or checking
 * in on the progress of an existing job.
 *
 * If you call this function multiple times
 * with the same job_id and it will only ever
 * start one timer loop at a time.
 */
function startJobChecker(job_id, command_name, retry_seconds, completed_callback_function=function(){}, indicationTarget="") {
    if (running_jobs_being_checked.has(job_id)) {
        addNotification('We are already checking on the status of ' +
                         command_name + '. Refresh the page to try again.');
    }
    else {
        running_jobs_being_checked.add(job_id);
        const lines_to_start_with = 20;
        running_jobs_line_number[job_id] = Math.max(0, get_largest_id('jobid_' + job_id) - lines_to_start_with); // <-- reset the line number
        latest_jobs_error_message[job_id] = ''; // <-- reset
        addNotification('We will check on the status of ' +
                         command_name + ' (job ' + job_id + ') every ' +
                         retry_seconds + ' seconds.');
        jobChecker(job_id, completed_callback_function, retry_seconds, command_name, indicationTarget);
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * By convention (2020-05-18):
 * image_id can be either an integer, or null (future: or "*")
 *
 * This returns either false if none are found,
 * or the job id of a job on the server which
 * is either in the "RUNNING" or "QUEUE" state.
 *
 */
function getUnfinishedJobId(project_id, image_id, command_name) {

    // prepare the filters
    // https://flask-restless.readthedocs.io/en/stable/searchformat.html#operators
    const table_name = 'job';

    const col_names  = [   'projId', 'imageId',        'cmd',            'status' ];
    const operations = [       '==',      '==',         '==',                'in' ];
    const values     = [ project_id,  image_id, command_name, ['RUNNING','QUEUE'] ];

    // query the database
    const sort = null; const limit = 1;
    const query_results = getDatabaseQueryResults(
        table_name, col_names, operations, values, sort, limit);

    // parse the results
    if (query_results.status != 200) {
        alert('Unknown error querying database for unfinished jobs.')
        return;
    }
    if (!query_results.data.num_results) {
        return false;
    }

    // get the results
    const job = query_results.data.objects[0];
    return job.id;
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * Immediately start a new job checker timer for
 * an unfinished job with the given command name,
 * or do nothing if it doesn't exist.
 */
function startJobCheckerIfExists(project_id, image_id, command_name, completed_callback_function, indicationTarget ='') {
    const retry_seconds = 5; // note: this value is usually received from the backend but we're using a default value
    const job_id = getUnfinishedJobId(project_id, image_id, command_name);
    if (job_id) {
        addNotification('We found a running job for ' + command_name +
                         ' (job ' + job_id + ') ' +
                         'and will report progress on it.');
        startJobChecker(job_id, command_name, retry_seconds, completed_callback_function, indicationTarget);
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * Load up timers for all running jobs associated with this project.
 */
function loadRunningJobsForProject(project_id, completed_callback_function = function(){}) {
    commands_to_check = ['make_patches', 'train_autoencoder', 'make_embed'];
    image_id = null;
    commands_to_check.forEach(command => startJobCheckerIfExists(
        project_id, image_id, command, completed_callback_function));
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * \brief Keep trying to reload an object at regular intervals (from json data) and run a function once loaded.
 *
 * Once the json response from the server indicates that the object is ready, a function
 * will be called.
 *
 * The following status codes are caught by this function:
 *   0 (ignored)
 *   200 (when the object is ready)
 *   202 (when the request for the object has been received)
 *   409 (when the object is not ready but the server is working on it)
 *   400 (for errors)
 *
 * For any other status code, the function will stop and an error
 * will be displayed if ignoreError is set to false.
 *
 * Once the object is ready, completed_callback_function() will be called.
 *
 * Usage example:
 *   runThisOnceRead = function(url) { do_something_with(url); };
 *   loadObjectAndRetry(api_image_url, runThisOnceRead.bind(null, url));
 *
 */
function loadObjectAndRetry(url, completed_callback_function=function(){}, ignoreError=false, indicationTarget="") {

    const requester = new XMLHttpRequest();
    requester.addEventListener('load', function() {

        let job_id;
        let json_output;
        try {
            json_output = JSON.parse(requester.responseText);
            job_id = json_output.job.id;
        }
        catch(e) {}

        const status_code = requester.status;
        switch(status_code) {

            case 202:
            case 409:
                const job_id = json_output.job.id;
                const command_name = json_output.job.cmd;
                const retry_seconds = json_output.retry;
                try {
                    updateTrafficLight(indicationTarget,colorRUNNING)
                }
                catch(e) {}
                startJobChecker(job_id, command_name, retry_seconds, completed_callback_function, indicationTarget);
                break;

            case 200:
                completed_callback_function();
                try {
                    updateTrafficLight(indicationTarget,colorAVAILABLE)
                }
                catch(e) {}
                break;

            case 400:
                if (!ignoreError) {
                    showWindowMessage('ERROR 400: ' + json_output.error, 'HTML Error');
                }
                try {
                    updateTrafficLight(indicationTarget, colorNOTAVAILABLE)
                } catch (e) {}
                break;
            default:
                if (!ignoreError) {
                    showWindowMessage('ERROR ' + status_code + ': (Unknown error)', 'HTML Error');
                 }
        }
    });

    const async = true;
    requester.open("GET", url, async);
    requester.send();
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * This function is used to update the status of the traffic light indication
 * Red - notavailable
 * Yellow - running
 * Green - available
 */
function updateTrafficLight(indicationTarget,status){
    document.getElementById(indicationTarget+'-dot').style.backgroundColor = status;
}
////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * This is the same as loadObjectAndRetry except
 * the url is assumed to contain an image, and when it's
 * ready it will paint it onto the context and then
 * call loadedFunction()
 */
function loadImageAndRetry(url, context, image_loaded_callback, ignore_error=false, indicationTarget="") {

    // we will create a custom function to draw the image onto the context:
    const on_image_ready = function(url) {

        // create a new temporary image:
        let temp_image = new Image();

        temp_image.onload = function() {
            context.drawImage(temp_image, 0, 0);
            image_loaded_callback();
        }

        // give it the url of the readied image:
        temp_image.src = url;
    };

    // call the master loading function:
    loadObjectAndRetry(url, on_image_ready.bind(null, url), ignore_error, indicationTarget);

}; // loadImageAndRetry
////////////////////////////////////////////////////////////////////////////////////////////////////

////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * This is the similar as loadObjectAndRetry except
 * the url is assumed to download a file, and when it's
 * ready it will call completed_callback_function()
 */
function downloadObject(url,completed_callback_function=function(){}, ignoreError=false) {
    const downloader = new XMLHttpRequest();
    downloader.addEventListener('load', function() {

        let json_output;
        try {
            json_output = JSON.parse(downloader.responseText);
        }
        catch(e) {}

        const status_code = downloader.status
        switch (status_code){
            case 202:
            case 200:
                let link = document.createElement('a');
                link.href = downloader.responseURL;
                link.download="";
                link.click();
                break;

            case 400:
                if (!ignoreError) {
                    showWindowMessage('ERROR 400: ' + json_output.error, 'HTML Error');
                }
                break;
        }
    })

    const async = true;
    downloader.open("GET", url, async);
    downloader.send();

}
////////////////////////////////////////////////////////////////////////////////////////////////////

////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * Show a little popup for errors or warnings and auto-close it after some seconds (0 to disable);
 */
function showWindowMessage(boxMessage,boxTitle="Error Message", autocloseSeconds=0) { //use for error messages

    addNotification(boxMessage);

    // a function to close the dialog:
    let closeDialog = function(dialog) { dialog.close(); };

    // closing options:
    let secondsToClose, buttonLabel = 'Close';
    if (autocloseSeconds > 0) {
        secondsToClose = autocloseSeconds;
        // update the button label too:
        buttonLabel = buttonLabel + ' (Autocloses in ' + secondsToClose + ' seconds)';
    }
    else {
        // if we're disabling autoclose, tell it to wait a really long time:
        secondsToClose = 100000000;
    }

    // actually show the dialog:
    BootstrapDialog.show({
        size: BootstrapDialog.SIZE_LARGE,
        title: boxTitle,
        message: boxMessage,
        // show a close button:
        buttons: [{label: buttonLabel, action: closeDialog } ],
        // start a timer once it's shown to autoclose:
        onshow: function(dialog) { setTimeout(function() { closeDialog(dialog); }, secondsToClose * 1000); }
    }); // show

} // showWindowMessage
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function getCurrentTime() {
  let d = new Date();
  let currentTime;
  let h = addZero(d.getHours());
  let m = addZero(d.getMinutes());
  let s = addZero(d.getSeconds());
  currentTime = h + ":" + m + ":" + s+"    ";
  currentTime = currentTime.toString();
  return currentTime
}

function addZero(i) {
  if (i < 10) {
    i = "0" + i;
  }
  return i;
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * This will pull out any url parameters:
 * (from https://davidwalsh.name/query-string-javascript)
 */
function getUrlParameter(name) {
  name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
  var regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
  var results = regex.exec(location.search);
  return results === null ? '' : decodeURIComponent(results[1].replace(/\+/g, ' '));
};
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
// for which log to show
var current_log = ''
function show_log(evt, which_log) {

  // update the css:
  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }
  evt.currentTarget.className += " active";

  // update the log data:
  current_log = which_log;
  update_log()

}

// start live streaming the log
var log_streaming_id;
function start_live_stream_log() {
  // start streaming the log
  let seconds_between_updates = 1
  log_streaming_id = window.setInterval(update_log, seconds_between_updates * 1000);
} // live_stream_log

function stop_live_stream_log() {
  // stop streaming the log
  window.clearInterval(log_streaming_id);
} // live_stream_log

// update the log inside of a text box
function update_log() {
  let text_area = document.getElementById('log');
  // a blank log will update the notifications
  let log_messages = (current_log == '') ? (get_notifications_as_text()) : get_log_messages(current_log);
  text_area.value = log_messages;
  text_area.scrollTop = text_area.scrollHeight;
} // update_log
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * This will return the latest output from a log file.
 */
function get_log_messages(log_name) {

  // this endpoint will give us the most recent log data:
  let url = "/api/logs/" + log_name;

  // pull the json data:
  let requester = new XMLHttpRequest()
  requester.open("GET", url, false);
  requester.send()
  return requester.responseText;

} // get_log_messages
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * Perform a filtered query on the database.
 * Give it a table name,
 * the name of a column,
 * an operation (e.g. '>=')
 * and a value.
 *
 * It will return a json containing
 * an html status code and and the response
 * data as a string.
 *
 * You can optionally input ascend sorting on the column
 * as true, false, or null (default)
 * in which the default is to do no sorting on the given column.
 *
 * You can optionally input a limit as an integer or null (default)
 * in which the default is not to limit the number of results returned.
 *
 * Optionally, if you have col_name, operation, and value as arrays instead
 * of single values, then it will create multiple filters on the database.
 * If you do this, the first column name will be used for any sorting.
 *
 * You can pass in null for the value and '==' or '!=' to the operation
 * for it to handle that properly.
 */
function getDatabaseQueryResults(table_name, col_name, operation, value,
                                    ascend = null,
                                    max_results = null) {

    // ensure everything is an array
    if (!(Array.isArray(col_name) && Array.isArray(operation) && Array.isArray(value) &&
            col_name.length === operation.length &&
            operation.length === value.length)) {
        col_name = [col_name];
        operation = [operation];
        value = [value];
    }

    // create filter objects
    filters = [];
    for (let i = 0; i < col_name.length; i++) {

        // https://flask-restless.readthedocs.io/en/stable/searchformat.html
        let new_filter;
        const new_col_name = col_name[i];
        let new_operation = operation[i];
        const new_value = value[i];

        if (new_value == null) {
            // special handling of null values in the operations
            if (new_operation == '==') {
                // https://flask-restless.readthedocs.io/en/1.0.0b1/fetching.html#filter-objects
                new_operation = 'is_null';
            }
            else if (new_operation == '!=') {
                new_operation = 'is_not_null';
            }
            else {
                alert('Unfamiliar operation paired with null in database query.');
            }
            new_filter = {name: new_col_name, op: new_operation};
        }
        else {
            new_filter = {name: new_col_name, op: new_operation, val: new_value};
        }

        filters.push(new_filter)
    }
    let query = {filters: filters};

    // set up sorting and max results
    if (ascend != null) {
        query.order_by = [{field: col_name[0], direction: ascend ? 'asc' : 'desc'}];
    }
    if (max_results != null) {
        query.limit = max_results;
    }

    // https://stackoverflow.com/a/57067829
    const target = new URL('/api/db/' + table_name, window.location.origin);
    target.search = (new URLSearchParams({q: JSON.stringify(query)})).toString();

    // send the request
    const requester = new XMLHttpRequest();
    const async = false;
    requester.open("GET", target, async);
    requester.send();

    // handle the response
    const status = requester.status;
    let response;
    try { response = JSON.parse(requester.responseText) } catch (e) {}
    if (status !== 200) {
      const error_message = (status === 404) ?
        ('ERROR: Table ' + table_name + ' not found in database.') :
        ('ERROR ' + status + ' upon querying database: ' + response.message);
      showWindowMessage(error_message);
    }

    return {status: status, data: response};
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * This will return the largest id in a database table, or
 * -1 if none exist.
 */
function get_largest_id(table_name) {

    // prepare
    const col_name = 'id';
    const operation = '!=';
    const value = 0;
    const ascend = false;  // <!-- descend
    const max_results = 1;  // <!-- either 1 or 0 results

    // query
    response = getDatabaseQueryResults(table_name, col_name, operation, value, ascend, max_results);

    // parse
    if (response.status == 200) {
        if (response.data.num_results == 0) { return 0; }
        else { return response.data.objects[0].id; }
    }
    else {
        // an error occurred
        return 0;
    }
    return response;

} // get_job_notifications
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * This will return the recent notifications for a given job at a given line, along with the html status code.
 */
function get_job_notifications(job_id, line_number) {

  const table_name = 'jobid_' + job_id;
  const col_name = 'id';
  const operation = '>=';
  const value = line_number;

  response = getDatabaseQueryResults(table_name, col_name, operation, value);

  return response;

} // get_job_notifications
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * This will output the status for a given job in
 * a string, such as "DONE", "QUEUE", "ERROR", "RUNNING".
 *
 * If the job was not found in the database, it will return an empty string.
 */
function get_job_status(job_id) {

  const table_name = 'job';
  const col_name = 'id';
  const operation = '==';
  const value = job_id;

  response = getDatabaseQueryResults(table_name, col_name, operation, value);

  return response.data.num_results == 0 ? '' : response.data.objects[0].status;
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * The following javascript code allows for a modal popup
 * div element that will close upon clicking a span (presumably
 * containing an "X").
 *
 * It expects the div element's id to be "modal_div" with class "modal".
 * It expects an inner div element to contain the content with class "model-content".
 * It expects button's id to be "modal_button"
 * It expects the span's class to be "close".
 *
 * Adapted from https://www.w3schools.com/howto/howto_css_modals.asp
 */
function prepareModal() {
  // Get the modal:
  var modal_div = document.getElementById("modal_div");
  // Get the button that opens the modal:
  var modal_button = document.getElementById("modal_button");
  // Get the <span> element that closes the modal:
  var modal_span = document.getElementsByClassName("close")[0];
  // When the user clicks on the button, open the modal:
  if (modal_button !== null) {
    modal_button.onclick = function() {
      modal_div.style.display = "block";
      start_live_stream_log();
    }
    // When the user clicks on <span> (x), close the modal:
    modal_span.onclick = function() {
      modal_div.style.display = "none";
      stop_live_stream_log();
    }
  }
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * The function sets a cookie by adding together the cookiename, the cookie value, and the expires string
 *
 * cname:  the name of the cookie
 * cvalue:  the value of the cookie
 * expays:  the number of days until the cookie should expire
 *
 * Modified from https://www.w3schools.com/js/js_cookies.asp
 */
function setCookie(cname, cvalue, exdays) {
    let d = new Date();
    d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
    let expires = "expires=" + d.toGMTString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
}


/**
 * The function takes the cookiename as parameter (cname)
 * If the cookie is found, return the value of the cookie
 * If the cookie is not found, return "".
 *
 * cname:  the name of the cookie
 *
 * Modified from https://www.w3schools.com/js/js_cookies.asp
 */
function getCookie(cname) {
    let name = cname + "=";
    let decodedCookie = decodeURIComponent(document.cookie);
    let ca = decodedCookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}






