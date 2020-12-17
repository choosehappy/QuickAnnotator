
////////////////////////////////////////////////////////////////////////////////////////////////////
function init() {
    prepareModal();
    updateImagePageButton();
    loadRunningTimers();
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function loadRunningTimers() {
    const project_id = "{{ project.id }}";
    const completed_callback_function = updateImagePageButton;
    loadRunningJobsForProject(project_id, completed_callback_function);
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function updateImagePageButton() {
    updateMakePatches();
    updateTrainAE();
    updateMakeEmbed();
    updateViewEmbed();
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function updateMakePatches() {
    let table_name = 'image';
    let col_name = 'projId';
    let operation = '==';
    let value = "{{ project.id }}";
    let numImage = getDatabaseQueryResults(table_name, col_name, operation, value).data.num_results;
    if (numImage == 0) {
        document.getElementById("makePacthButton").disabled = true;
        document.getElementById("makePacthButton").title = "'Make Patches' is NOT ready to use."
    } else {
        document.getElementById("makePacthButton").disabled = false;
        document.getElementById("makePacthButton").title = "'Make Patches' is ready to use."
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function updateTrainAE() {
    let table_name = 'project';
    let col_name = 'id';
    let operation = '==';
    let value = "{{ project.id }}";
    let make_patches_time = getDatabaseQueryResults(table_name, col_name, operation, value).data.objects[0].make_patches_time;
    if (make_patches_time == null) {
        document.getElementById("trainAEButton").disabled = true;
        document.getElementById("trainAEButton").title = "'(Re)train Model 0' is NOT ready to use."
    } else {
        document.getElementById("trainAEButton").disabled = false;
        document.getElementById("trainAEButton").title = "'(Re)train Model 0' is ready to use."
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function updateMakeEmbed() {
    let table_name = 'project';
    let col_name = 'id';
    let operation = '==';
    let value = "{{ project.id }}";
    let train_ae_time = getDatabaseQueryResults(table_name, col_name, operation, value).data.objects[0].train_ae_time;
    let iteration = getDatabaseQueryResults(table_name, col_name, operation, value).data.objects[0].iteration;
    if (iteration == -1) {
        document.getElementById("makeEmbedButton").disabled = true;
        document.getElementById("makeEmbedButton").title = "'Embed Patches' is NOT ready to use.";
    } else if (train_ae_time == null && iteration ==0){
        document.getElementById("makeEmbedButton").disabled = true;
        document.getElementById("makeEmbedButton").title = "The latest model is model 0. The Model 0 is being retrained. No other DL model is available at this moment. \n" +
            "Make_embed is currently unavailable"
    }
    else {
        document.getElementById("makeEmbedButton").disabled = false;
        document.getElementById("makeEmbedButton").title = "'Embed Patches' is ready to use.";
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function updateViewEmbed() {
    let table_name = 'project';
    let col_name = 'id';
    let operation = '==';
    let value = "{{ project.id }}";
    let embed_iteration = getDatabaseQueryResults(table_name, col_name, operation, value).data.objects[0].embed_iteration;
    if (embed_iteration == -1) {
        document.getElementById("viewEmbedButton").disabled = true;
        document.getElementById("viewEmbedButton").title = "'View Embedding' is NOT ready to use.";
    } else {
        document.getElementById("viewEmbedButton").disabled = false;
        document.getElementById("viewEmbedButton").title = "'View Embedding' is ready to use.";
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function train_ae() {
    addNotification("'(Re)train Model 0' Pressed.")
    if (checkMake_embed()) {
        addNotification("The latest model is model 0. The Model 0 is being retrained. No other DL model is available at this moment. \n" +
            "Make_embed is currently unavailable")
        document.getElementById("makeEmbedButton").disabled = true;
        document.getElementById("makeEmbedButton").title = "The latest model is model 0. The Model 0 is being retrained. No other DL model is available at this moment. \n" +
            "Make_embed is currently unavailable"
    }
    const run_url = new URL("{{ url_for('api.train_autoencoder', project_name=project.name) }}", window.location.origin);
    return loadObjectAndRetry(run_url, updateImagePageButton)
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function make_patches() {
    addNotification("'Make Patches' Pressed.")
    // Using URL instead of string here
    const run_url = new URL("{{ url_for('api.make_patches', project_name=project.name) }}", window.location.origin)
    let $dialog = $('<div></div>').html('SplitText').dialog({
        dialogClass: "no-close",
        modal: true,
        title: "Make Patches",
        // We have three options here
        buttons: {
            // Remove the white background when making patches
            "Remove": function () {
                run_url.searchParams.append("whiteBG", "remove")
                $dialog.dialog('close');
                addNotification("'Make Patches' (White Background Removed) starts.")
                return loadObjectAndRetry(run_url, updateImagePageButton)
            },
            // Keep the white backgeound when making patches
            "Keep": function () {
                $dialog.dialog('close');
                addNotification("'Make Patches' (White Background Kept) starts.")
                return loadObjectAndRetry(run_url, updateImagePageButton)
            },
            // Simply close the dialog and return to original page
            "Cancel": function () {
                addNotification("'Make Patches' cancels.")
                $dialog.dialog('close');
            }
        }
    });
    $dialog.html("Do you want to remove the white background from the patches?")
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function make_embed() {
    addNotification("'Embed Patches' Pressed.")
    const run_url = new URL("{{ url_for('api.make_embed', project_name=project.name) }}", window.location.origin)
    return loadObjectAndRetry(run_url, updateImagePageButton);
}
////////////////////////////////////////////////////////////////////////////////////////////////////
function checkMake_embed() {
    let table_name = 'project';
    let col_name = 'id';
    let operation = '==';
    let value = "{{ project.id }}";
    let train_ae_time = getDatabaseQueryResults(table_name, col_name, operation, value).data.objects[0].train_ae_time;
    let iteration = getDatabaseQueryResults(table_name, col_name, operation, value).data.objects[0].iteration;
    // Latest model is model 0 and model 0 is being retrain.
    if (train_ae_time != null && iteration == 0) {
        return true;
    }
}

////////////////////////////////////////////////////////////////////////////////////////////////////
function delete_image(image_name) {
    let xhr = new XMLHttpRequest();
    let $dialog = $('<div></div>').html('SplitText').dialog({
        dialogClass: "no-close",
        modal: true,
        title: "Delete Image",
        buttons: {
            "Delete": function () {
                $dialog.dialog('close');
                addNotification(`Delete the image: '${image_name}'.`);
                let run_url = "{{ url_for('api.delete_image', project_name = project.name, image_name= '') }}" + image_name;
                xhr.onreadystatechange = function () {
                    if (this.readyState == 1 && this.status == 0) {
                        // This is to display the block of the image as none; it is kept multiple browsers
                        document.getElementById(image_name).style.display = "none";
                        // Remove the html linked to the deleted image
                        document.getElementById(image_name).outerHTML = "";
                    }
                };
                xhr.open("DELETE", run_url, true);
                xhr.send();

            },
            // Simply close the dialog and return to original page
            "Cancel": function () {
                addNotification(`Delete Image '${image_name}' cancels.`)
                $dialog.dialog('close');
            }
        }
    });
    $dialog.html("Do you want to delete the selected image?")
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function updatePercentCompleted(width, height, ppixel, npixel, elementID) {
    let totalPixel = Number(width) * Number(height) / 100 // For stability concern
    let annotatedPixel = Number(ppixel) + Number(npixel)
    let percent_completed = annotatedPixel / totalPixel;
    document.getElementById(elementID).innerHTML = Math.ceil(percent_completed) + "%";
}
////////////////////////////////////////////////////////////////////////////////////////////////////
