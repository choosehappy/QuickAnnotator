


////////////////////////////////////////////////////////////////////////////////////////////////////
function setScroll() {
	scrollV = document.documentElement.scrollTop;
	scrollH = document.documentElement.scrollLeft;
}
////////////////////////////////////////////////////////////////////////////////////////////////////

////////////////////////////////////////////////////////////////////////////////////////////////////
// The global listener web page
function prepareGlobalListeners(which_context) {
    // Placeholder
    which_context.onmousedown = function(e) {

    }
    which_context.onmouseup = function (e) {
        annotatorEnabled = true;
        bgImageEnabler = true;
    }

}

////////////////////////////////////////////////////////////////////////////////////////////////////
// The listener on the background canvas
function prepareMouseListeners(which_canvas) {

    which_canvas.onmousedown = function (e) {
        if (e.button != 0) return; // Make sure it is left clicked
        let center_x = Math.round(e.clientX - canvas_mask.offsetLeft + scrollH);
        let center_y = Math.round(e.clientY - canvas_mask.offsetTop + scrollV);
        // Check whether the user has started making annotation
        if (alreadyMakingAnnotation) {
            let $dialog = $('<div></div>').html('SplitText').dialog({
                // Force user to make a choice
                dialogClass: "no-close",
                modal: true,
                width: 450,
                title: "Warning: Your current annotation is not saved yet!",
                buttons: {
                    "Confirm Deletion": function () {
                        $dialog.dialog('close');
                        clearArea();
                        // Below state is set in clearAre, it depends on whether user want to still keep the ROI after clicking confirm
                        // alreadyMakingAnnotation = false;

                        showRect(center_x, center_y);
                        redrawCroppedTool();
                        // initialize annotation undo and redo
                        initAnnotationHistory();
                    },
                    "Continue Annotation": function () {
                        $dialog.dialog('close');
                    }
                }
            });
            $dialog.html("Your current annotation is not saved yet! <br> <b>Are you sure you want to lose this annotation</b>?" +
                "<br> Directions for saving the annotation here:"+
                "<br> 1. Upload the annotation patches (Hot key: H)" +
                "<br> 2. Select the filling region" +
                "<br> 3. Add to training/test sets"
            )
        } else {
            // Now the user continues with next patches
            alreadyMakingAnnotation = false;
            // This is to disable the annotation tool when user is moving the selection rectangle on the image
            annotatorEnabled = false;
            mousePressed = true;
            showRect(center_x, center_y);
        }
    };

    which_canvas.onmousemove = function (e){
        if (e.button != 0) return; // Make sure it is left clicked

        // Check whether we allow the user to operate on the imagebg, eg they pressed mouse the annotator and move to the bgImage
        if (!bgImageEnabler) return
        // We neither disable nor enable annotatorEnabled
        if (mousePressed){
            let center_x = Math.round(e.clientX - canvas_mask.offsetLeft + scrollH);
            let center_y = Math.round(e.clientY - canvas_mask.offsetTop + scrollV);
            showRect(center_x, center_y);
        }
    };

    which_canvas.onmouseup = function (e)
    {
        if (e.button != 0) return; // Make sure it is left clicked
        // Check whether we allow the user to operate on the imagebg, eg they pressed mouse the annotator and move to the bgImage
        if (!bgImageEnabler) return
        // This is to enable pathologist to use the annotator
        // We should set mouse not pressed on image in both mouse key listener
        annotatorEnabled = true;
        mousePressed = false;
        removeSelection();

        ctx_cropped_bg.setTransform(1, 0, 0, 1, 0, 0);
        ctx_cropped_bg.clearRect(0, 0, annotatorSize, annotatorSize);

        ctx_cropped_mask.setTransform(1, 0, 0, 1, 0, 0);
        ctx_cropped_mask.clearRect(0, 0, annotatorSize, annotatorSize);

        cropped_center_x = Math.round(e.clientX - canvas_mask.offsetLeft + scrollH);
        cropped_center_y = Math.round(e.clientY - canvas_mask.offsetTop + scrollV);
        showRect(cropped_center_x, cropped_center_y);

        redrawCroppedTool();

        // initialize annotation undo and redo
        initAnnotationHistory();

    };

} // cropRegion
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// Functions controlling the selection rectangle on the large window:

function showRect(centerX, centerY){
    //I reset the globalAlpha for ctx_cropped_bg because it was set to 0.3 when #}
    ctx_cropped_bg.globalAlpha=1;
    removeSelection();
    actualCropSize =  Math.round(canvasWidth / canvas_bg_ori.width * cropSize);
    leftUpperPt_x = Math.round(centerX - actualCropSize/2);
    leftUpperPt_y = Math.round(centerY - actualCropSize/2);

    // stop moving when the box encountering the edge
    if (leftUpperPt_x < 0) leftUpperPt_x = 0;
    else if (leftUpperPt_x > canvasWidth - actualCropSize) leftUpperPt_x = canvasWidth - actualCropSize;

    if (leftUpperPt_y < 0) leftUpperPt_y = 0;
    else if (leftUpperPt_y > canvasHeight - actualCropSize) leftUpperPt_y = canvasHeight - actualCropSize;

    ctx_bg.shadowBlur = 5;
    ctx_bg.shadowColor = "white";
    ctx_bg.strokeStyle = 'white';
    ctx_bg.lineWidth = 10;
    ctx_bg.strokeRect(leftUpperPt_x, leftUpperPt_y, actualCropSize, actualCropSize);
    ctx_bg.strokeStyle = 'black';
    ctx_bg.lineWidth = 3;
    ctx_bg.strokeRect(leftUpperPt_x, leftUpperPt_y, actualCropSize, actualCropSize);
    ctx_bg.strokeStyle = 'white';
    ctx_bg.lineWidth = 1;
    ctx_bg.strokeRect(leftUpperPt_x, leftUpperPt_y, actualCropSize, actualCropSize);
    ctx_bg.stroke();
}

function removeSelection(){
    ctx_bg.setTransform(1, 0, 0, 1, 0, 0);
    ctx_bg.clearRect(0, 0, canvasWidth, canvasHeight);
    ctx_bg.drawImage(canvas_bg_ori, 0, 0, canvasWidth, canvasHeight);
}

function restoreSelection(){
    showRect(cropped_center_x, cropped_center_y);
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// Update the annotation mask on the main window to reflect ctx_mask_ori
function redrawMask() {

    const url = "{{ url_for('api.get_rois_for_image', project_name=project.name, image_name=image.name)}}"
    fetch(url)
        .then(
            response => response.json()
        )
        .then(rois => {
            // draw it from the canvas_mask_ori data
            ctx_mask.clearRect(0, 0, canvasWidth, canvasHeight);
            ctx_mask.drawImage(canvas_mask_ori, 0, 0, canvasWidth, canvasHeight);

            // give it some alpha blending
            setAlphaChannel(ctx_mask, 127, 0);

            drawMaskBorders(rois)
        })

} // redrawMask
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function drawMaskBorders(rois) {
    for (const roi of rois) {

        const image_width = parseInt("{{image.width}}")
        const image_height = parseInt("{{image.height}}")

        const scale_x = canvasWidth / image_width
        const scale_y = canvasHeight / image_height
        
        const x = roi.x * scale_x
        const y = roi.y * scale_y
        const w = roi.width * scale_x
        const h = roi.height * scale_y

        const in_testing = roi.testingROI == 1
        const in_training = roi.testingROI == 0

        let stroke_color;
        let alpha = 0.50
        alpha = alpha.toString()
        
        if (in_testing) {
            stroke_color = 'rgba(0,255,0,' + alpha + ')'
        }
        else if (in_training) {
            stroke_color = 'rgba(255,255,0,' + alpha + ')'
        }
        else {
            stroke_color = 'rgba(0,0,0,' + alpha + ')'
        }

        context = ctx_mask

        context.strokeStyle = stroke_color
        context.lineWidth = 8
        context.strokeRect(x, y, w, h)

        context.strokeStyle = 'white'
        context.lineWidth = 1
        context.strokeRect(x, y, w, h)

        ctx_bg.stroke()
    
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
// Functions controlling the deep learning:

// Redraw an already-loaded one
function redrawPrediction() {
    ctx_result.clearRect(0, 0, canvasWidth, canvasHeight);
    ctx_result.drawImage(canvas_result_ori, 0, 0, canvasWidth, canvasHeight);
    setAlphaChannel(ctx_result, 127, 127);
}

// Reload it from the backend
function reloadPrediction() {

    // when the dl result is ready, call this function:
    let dlResultReady = function() {
        addNotification('New deep learning prediction ready. Redrawing now.')
        redrawPrediction();
        prediction_loaded = true;
        enableToolButton();
    }; // drawSuperpixels
    
    // load the prediction image to apply the dl result:
    let prediction_url = "{{ url_for('api.get_prediction', project_name=project.name, image_name=image.name)}}";        
    ignore_errors = true;
    loadImageAndRetry(prediction_url, ctx_result_ori, dlResultReady, ignore_errors, 'prediction');
}

// trigger an ai retraining and a redrawing of the prediction mask:
function retrain_deep_learning(frommodelid){

    addNotification("Retrain DL starts. Please wait.");

    let run_url = new URL("{{ url_for('api.retrain_dl', project_name=project.name) }}", window.location.origin);
    run_url.searchParams.append('frommodelid',frommodelid)
    return loadObjectAndRetry(run_url, reloadPrediction,false, 'model');

}  // retrain_deep_learning

// deep learning functions
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
// Functions controlling which layers to show/hide:

function hideLayers() {
    canvas_mask.style.visibility = 'hidden';
    canvas_result.style.visibility = 'hidden';
    canvas_cropped_mask.style.visibility = "hidden";
    canvas_cropped_result.style.visibility = "hidden";
}

function showDLInternal() {
    if (!prediction_loaded) {
        addNotification('Warning: No DL prediction has been generated yet.');
        return;
    }
    canvas_result.style.visibility = 'visible';
    canvas_cropped_result.style.visibility = "visible";
}

function showMaskInternal() {
    canvas_mask.style.visibility = 'visible';
    canvas_cropped_mask.style.visibility = "visible";
}

function showHideLayers(layer_name, show_mask = false, show_result = false) {
    layer = layer_name;
    hideLayers();
    if (show_mask) showMaskInternal();
    if (show_result) showDLInternal();
    restoreSelection();
    enableToolButton();
}

function showOriginal(){
    showHideLayers("origin")
    enableToolButton();
} // showOriginal

function showAnnotation(){
    showHideLayers("annotation", show_mask = true)
    enableToolButton();
}

function showDLFusedAnnotation(){
    showHideLayers("fuse", show_mask = true, show_result = true);
    enableToolButton();
}

function showDLResult() {
    showHideLayers("prediction", show_mask = false, show_result = true);
    enableToolButton();
}

// layers
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// Set the alpha channel of pixels (0-255)
function setAlphaChannel(context, alpha_for_nonblack, alpha_for_black = 0) {
    const w = context.canvas.width;
    const h = context.canvas.height;
    const image_data = context.getImageData(0, 0, w, h);
    const raw_data = image_data.data;
    for (let i = 0; i < raw_data.length; i += 4) {
        raw_data[i+3] = (raw_data[i+0] || raw_data[i+1] || raw_data[i+2]) ?
            alpha_for_nonblack : alpha_for_black;
    }
    context.putImageData(image_data, 0, 0);
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * Upload a canvas (sent with a given "variableName") to a given url
 * and call success_callback(parsed_json) upon a successful upload.
 */
function uploadCanvasImage(url, variableName, canvas, templateFormData, success_callback) {

    // upload the image patch at this region of interest
    let new_form_data = templateFormData;
    let data_URL = canvas.toDataURL("image/png");
    new_form_data.append(variableName, data_URL);
    let xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function(){
        if (this.readyState == 4){
            response = JSON.parse(this.responseText);
            if (this.status == 201) {
                addNotification('Canvas uploaded to server.');
                success_callback(response);
            }
            else {
                addNotification('Canvas upload response: [' + this.status + '] ' + JSON.stringify(response));
            }
        }
    }
    xhr.open('POST', url, false);
    xhr.send(new_form_data);

    return xhr;

} // uploadCanvas
////////////////////////////////////////////////////////////////////////////////////////////////////


// Use XML Request to capture a jsonify response. A notification pops up and the browser stays on the same webpage if there is no previous or next image in the project
function prevnext(direction) {
       let xhr = new XMLHttpRequest()
       let url
       switch (direction) {
           case 'previous':
               url = "{{ url_for('api.prevnext_image', project_name=project.name, image_name=image.name,direction='previous') }}"
               break
           case 'next':
               url = "{{ url_for('api.prevnext_image', project_name=project.name, image_name=image.name,direction='next') }}"
               break
       }

       xhr.onreadystatechange = function(){
           if (this.readyState == 4 && this.status == 400) {
               let myArr = JSON.parse(this.responseText);
               showWindowMessage(myArr.error);
           }
           if (this.readyState == 4 && this.status == 200) {
               let myArr = JSON.parse(this.responseText);
               window.location.replace(myArr.url);
           }
       }
       xhr.open('GET', url , true);
       xhr.send();

}// PrevNext
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
// Set the zoom slider to be a given value (clamped) and update the image
function setZoomFactor(new_zoom_factor = 1.0) {
    const min_zoom_factor = parseFloat(zoom_factor_slider.min);
    const max_zoom_factor = parseFloat(zoom_factor_slider.max);
    zoom_factor_slider.value = Math.max(
        min_zoom_factor,
        Math.min(
            new_zoom_factor,
            max_zoom_factor));
    updateZoomFactor();
}

// pull the zoom factor from the slider and update the image
let updateZoomFactor = function() {

    // pull it
    zoom_factor = Number(zoom_factor_slider.value);

    // update the displayed value
    zoom_factor_value.innerHTML = zoom_factor;

    // convert to float
    zoom_factor = parseFloat(zoom_factor);

    // update height/widths
    canvasWidth = canvasWidth_ori * zoom_factor;
    canvasHeight = canvasHeight_ori * zoom_factor;

    document.getElementById('canvas').style.height = canvasHeight;

    canvas_bg.width = canvasWidth;
    canvas_bg.height = canvasHeight;

    canvas_mask.width = canvasWidth;
    canvas_mask.height = canvasHeight;

    canvas_result.width = canvasWidth;
    canvas_result.height = canvasHeight;

    // update the centroid for the new zoom factor
    cropped_center_x *= zoom_factor / previous_zoom_factor;
    cropped_center_y *= zoom_factor / previous_zoom_factor;
    previous_zoom_factor = zoom_factor;

    // redraw everything
    removeSelection();
    restoreSelection();
    redrawMask();
    redrawPrediction();
}

let updateAnnotatorSize = function() {

    // pull it
    annotatorSize = Number(annotator_size_slider.value)

    // update the displayed value
    annotator_size_value.innerHTML = annotatorSize

    // update the widget
    resetAnnotatorSize()
    resetClassButtonBackgrounds()
    redrawCroppedTool()

}

// Reset the zoom to fit the entire image in the window
function resetZoom() {
    const browser_width = window.innerWidth;
    const browser_height = window.innerHeight;
    const zoom_factor_to_see_full_width = browser_width / canvasWidth_ori;
    const zoom_factor_to_see_full_height = browser_height / canvasHeight_ori;
    const buffer = 0.9;  // <-- there might be margins, so try to zoom out a bit further
    const new_zoom_factor = Math.min(
        zoom_factor_to_see_full_height * buffer,
        zoom_factor_to_see_full_width * buffer);
    setZoomFactor(new_zoom_factor);
}

// (note: clamping is done in the "setZoomFactor" function)
function zoomIn() {
    setZoomFactor(previous_zoom_factor + parseFloat(zoom_factor_slider.step))
}
function zoomOut() {
    setZoomFactor(previous_zoom_factor - parseFloat(zoom_factor_slider.step))
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
// Reset the panels to snap to the screen edge
function resetPanels() {
    let margin = 20;

    let info_panel = document.getElementById('info');
    let annotator_panel = document.getElementById('annotator');

    let browser_width = window.innerWidth;
    let info_width = info_panel.offsetWidth;
    let info_height = info_panel.offsetHeight;
    let annotator_width = document.getElementById('toolbox').offsetWidth;

    let title_bar_bottom = document.getElementById('title').getBoundingClientRect().bottom;
    let info_heading_height = document.getElementById('infohandle').offsetHeight + margin;

    let new_info_left = browser_width - info_width - margin;
    let new_annotator_left = browser_width - annotator_width - margin;
    let new_info_top = title_bar_bottom + info_heading_height + margin;
    let new_toolbox_top = new_info_top + info_height + margin;

    info_panel.style.top = new_info_top + "px";
    annotator_panel.style.top = new_toolbox_top + "px";
    info_panel.style.left = new_info_left + "px";
    annotator_panel.style.left = new_annotator_left + "px";
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
// Recalculate the % of image we've annotated and display it.
function updatePercentCompleted() {
    const w = canvas_mask_ori.width;
    const h = canvas_mask_ori.height;
    mask_data = ctx_mask_ori.getImageData(0, 0, w, h).data;
    let nonzero_count = 0;
    for (let i = 0; i <mask_data.length; i+=4) {
        if (mask_data[i+0] || mask_data[i+1] || mask_data[i+1]) {
            nonzero_count++;
        }
    }
    const total_pixels = w*h;
    const percent_completed = nonzero_count/total_pixels*100;
    addNotification('% of image annotated = ' + Math.round(percent_completed*1000)/1000 + '%');
    document.getElementById('annotated_percentage').innerHTML = Math.ceil(percent_completed) + "%";
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
// https://stackoverflow.com/a/5624139
function rgbToHex(rgbArray) {
    return "#" + ((1 << 24) + (rgbArray[0] << 16) + (rgbArray[1] << 8) + rgbArray[2]).toString(16).slice(1);
}

function hexToRGB(hex) {
    var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}
////////////////////////////////////////////////////////////////////////////////////////////////////

// ////////////////////////////////////////////////////////////////////////////////////////////////////
function annotationDotToggle() {
    if (showAnnotationDot) {
        showAnnotationDot = false;
        document.getElementById('Annotation-dot').style.backgroundColor = colorOFF
    } else {
        showAnnotationDot = true;
        document.getElementById('Annotation-dot').style.backgroundColor = colorON
    }
    updateViewMode();

}

function predictionDotToggle() {
    if (showPredictionDot) {
        showPredictionDot = false;
        document.getElementById('Prediction-dot').style.backgroundColor = colorOFF
    } else {
        showPredictionDot = true;
        document.getElementById('Prediction-dot').style.backgroundColor = colorON
    }
    updateViewMode();

}

function updateViewMode() {
    if (showAnnotationDot) {
        if (showPredictionDot) {showDLFusedAnnotation()} else {showAnnotation()}
    } else if (showPredictionDot) {showDLResult()} else {showOriginal()}
}
////////////////////////////////////////////////////////////////////////////////////////////////////

