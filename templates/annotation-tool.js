

////////////////////////////////////////////////////////////////////////////////////////////////////
// Functions to assign the remaining pixels in the annotation window to a class:
function resetClassButtonBackgrounds() {

    const positiveButton = document.getElementById("btnPositive");
    const negativeButton = document.getElementById("btnNegative");
    const unknownButton = document.getElementById("btnUnknown");

    const defaultBackgroundColor = "#FFFFFF";
    positiveButton.style.backgroundColor = defaultBackgroundColor;
    negativeButton.style.backgroundColor = defaultBackgroundColor;
    unknownButton.style.backgroundColor = defaultBackgroundColor;

    let selectedButton;
    switch (annotation_class) {
        case "positive": selectedButton = positiveButton; break;
        case "negative": selectedButton = negativeButton; break;
        case "unknown": selectedButton = unknownButton; break;
        default: showWindowMessage("Unknown annotation class for button coloring."); return;
    }

    const currentColor = rgbToHex(getCurrentAnnotationRGB());
    const currentColorTransparent = currentColor + "77";
    selectedButton.style.backgroundColor = currentColorTransparent;
    ctx_cropped_mask.strokeStyle = currentColorTransparent;
    ctx_cropped_mask.fillStyle = currentColor;
}

// Create negative mask (negation of the mask):
function setToNegative() {
    annotation_class = "negative";
    resetClassButtonBackgrounds();
}
function setToUnknown(){
	annotation_class = "unknown";
	resetClassButtonBackgrounds();
}
function setToPositive(){
	annotation_class = "positive";
    resetClassButtonBackgrounds();
}

// pull the RGB value for the given class
function getCurrentAnnotationRGB() {
    switch (annotation_class) {
        case "positive":
            return positiveRGB;
        case "negative":
            return negativeRGB;
        case "unknown":
            return unknownRGB;
        default:
            showWindowMessage("Error: Unknown annotation class.");
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// Functions for enabling undo/redo:

/**
 * Initialize annotation history
 */
function initAnnotationHistory(){
    undo_list = [];
    saveAnnotationHistory();
}

/**
 * Save annotation history
 */
function saveAnnotationHistory(){
    // undo_list.push(canvas_cropped_mask.toDataURL("image/png"));
    undo_list.push(ctx_cropped_mask.getImageData(0, 0, annotatorSize, annotatorSize));
    redo_list = [];
}

/**
 * Redo - reverse the last annotation
 */
function undo(){
    if (undo_list.length) {
        const pop = undo_list.pop();
        redo_list.push(pop);
    }
    if (undo_list.length) {
        setCroppedMaskData(undo_list[undo_list.length-1]);
        addNotification('Last annotation drawing undone.')
    } else {
        clearArea();
    }
}

/**
 * Undo - redo the last annotation
 */
function redo(){
    if (!redo_list.length) return;
    let pop = redo_list.pop();
    undo_list.push(pop);
    setCroppedMaskData(pop);
    addNotification('Last annotation drawing redone.')
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// Check if a prediction exists, if so import it into the annotation tool
function importPrediction() {

    if (!prediction_loaded) {
        addNotification('Warning: No DL prediction available for import.');
        return;
    }

    // draw the result image on the canvas
    redrawCroppedTool(canvas_result_ori);

    // correct the colors
    const cropped_mask_data = ctx_cropped_mask.getImageData(0, 0, canvas_cropped_mask.width, canvas_cropped_mask.height);
    for (let i = 0; i < cropped_mask_data.data.length; i += 4) {
      const r = cropped_mask_data.data[i+0];
      const g = cropped_mask_data.data[i+1];
      const b = cropped_mask_data.data[i+2];
      const sum = r+g+b;
      if (sum==(255*3)) {
        // white in the prediction corresponds to cyan
        cropped_mask_data.data[i+0] = 0;
        cropped_mask_data.data[i+3] = 127;
      }
      //const a = cropped_mask_data.data[i+3];
    }

    // store corrected colors
    setCroppedMaskData(cropped_mask_data);

    saveAnnotationHistory();
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// set up the alpha channel of the mask to be as desired
function resetCroppedMaskAlpha() {
    setAlphaChannel(ctx_cropped_mask, 127, 0);
    setAlphaChannel(ctx_cropped_result, 127, 127);
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
// Draw cropped region on the small canvas with initial data from the full_mask
function redrawCroppedTool(full_mask = canvas_mask_ori, drawMaskOnCropped = true){

    // get the top corner of the image
    leftUpperx_ori = Math.round(leftUpperPt_x / canvasWidth * imgWidth);
    leftUppery_ori = Math.round(leftUpperPt_y / canvasHeight * imgHeight);

    // leftUpperPt_x leftUpperPt_y are not defined when first loading. This makes leftupperx/y_ori NAN
    if (isNaN(leftUpperx_ori)) leftUpperx_ori = 0;
    if (isNaN(leftUppery_ori)) leftUppery_ori = 0;

    function drawCroppedImage(full_canvas, output_context) {
        const old_composite_method = output_context.globalCompositeOperation;
    	output_context.globalCompositeOperation="copy";
        output_context.globalAlpha = 1; // superpixel boundary changes this so we reset it
        output_context.clearRect(0, 0, annotatorSize, annotatorSize);
        output_context.drawImage(full_canvas, leftUpperx_ori, leftUppery_ori, cropSize, cropSize, 0, 0, annotatorSize, annotatorSize);
    	output_context.globalCompositeOperation=old_composite_method;
    }

    // draw the result image at the cropped location
    drawCroppedImage(canvas_bg_ori, ctx_cropped_bg);
    if (drawMaskOnCropped) drawCroppedImage(full_mask, ctx_cropped_mask);
    drawCroppedImage(canvas_result_ori, ctx_cropped_result);

    // set up the alpha channel
    resetCroppedMaskAlpha();

    // get superpixel mask
    superpixel_data = ctx_superpixel_ori.getImageData(leftUpperx_ori, leftUppery_ori, cropSize, cropSize);
    superpixel_boundary_data = ctx_superpixel_boundary_ori.getImageData(leftUpperx_ori, leftUppery_ori, cropSize, cropSize);

} // redrawCroppedTool
////////////////////////////////////////////////////////////////////////////////////////////////////



// output true/false if we are allowed to annotate in this mode
function canAnnotate() {
    // we only allow annotating on certain modes
    if (!(layer == "fuse" || layer == "annotation")) {
        addNotification("Cannot annotate; this mode is read-only.");
        return false;
    }
    else {
        return true;
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
// check if this annotation area is ready for upload

function prepareForUpload() {

    if (!canAnnotate()) return;

    const w = annotatorSize;
    const h = annotatorSize;
    const mask_data = ctx_cropped_mask.getImageData(0, 0, w, h).data;

    // check if the mask has any un-annotated (pure black) pixels
    let hasAnyBlank = false;
    for (let i = 0; i < mask_data.length; i+=4) {
        if (!mask_data[i+0] && !mask_data[i+1] && !mask_data[i+2]) {
            hasAnyBlank = true;
            break;
        }
    }

    // any unknowns means that the region was not fully annotated
    document.getElementById('bg_fill_dialog').style.display = hasAnyBlank ? 'initial' : 'none';

    if (hasAnyBlank) {
        document.getElementById('radio_negative').checked=true;
        document.getElementById('radio_unknown').checked=false;
        replaceMaskBlack(negativeRGB);

        // when the user selects a background fill, fill it
        $('input[type=radio][name=bg_fill]').change(function () {
            if (this.value == 'fill_negative') {
                undo();
                replaceMaskBlack(negativeRGB);
            }
            else if (this.value == 'fill_unknown') {
                undo();
                replaceMaskBlack(unknownRGB);
            }
        });
    }

    $('#upload_dialog').dialog({
        dialogClass: "no-close",
        closeOnEscape: false,
        modal: true,
        title: "Finish and Upload Annotation",
        // We have three options here
        buttons: {
            // Remove the white background when making patches
            "Training": function () {
                addNotification("Adding to training dataset.");
                $(this).dialog('close');
                uploadMaskToServer('train')
            },
            // Keep the white backgeound when making patches
            "Testing": function () {
                addNotification("Adding to testing dataset.");
                $(this).dialog('close');
                uploadMaskToServer('test');
            },
            // Simply close the dialog and return to original page
            "Cancel": function () {
                addNotification("Canceling upload.");
                if (hasAnyBlank) undo(); // remove the bg fill
                $(this).dialog('close');
            }
        }
    });
}

function uploadMaskToServer(dataset) {

    if (!canAnnotate()) return;

    // take the completed new mask and give it to the contexts
    let leftUpperxOnMask = Math.round(leftUpperPt_x / canvasWidth * imgWidth);
    let leftUpperyOnMask = Math.round(leftUpperPt_y / canvasWidth * imgWidth);

    // prepare some default form data for the upload:
    let fd = new FormData();
    fd.append("pointx", leftUpperxOnMask);
    fd.append("pointy", leftUpperyOnMask);
    fd.append("force", true);

    // create an roi patch to upload:
    let canvas_roi = document.createElement("canvas");
    let ctx_canvas_roi = canvas_roi.getContext("2d");
    canvas_roi.width = cropSize;
    canvas_roi.height = cropSize;
    ctx_canvas_roi.imageSmoothingEnabled = false;
    ctx_canvas_roi.drawImage(canvas_cropped_mask, 0, 0, annotatorSize, annotatorSize, 0, 0, cropSize, cropSize);

    // for a successful roi patch upload
    const uploadCallback = function(parsed_json) {

        // redraw the mask data
        ctx_mask_ori.clearRect(leftUpperxOnMask, leftUpperyOnMask, cropSize, cropSize);
        ctx_mask_ori.drawImage(canvas_cropped_mask, 0, 0, annotatorSize, annotatorSize, leftUpperxOnMask, leftUpperyOnMask, cropSize, cropSize);
        redrawMask();

        // extract the roi's name from the server response:
        const roi_name = parsed_json.roi.name;

        // add that roi image to either the training or testing set:
        let xhr_add_to_traintest = new XMLHttpRequest();
        let url_add_to_traintest = "{{ url_for('api.add_roi_to_traintest', project_name=project.name, roiname='!!!!!', traintype='#####')}}"

        url_add_to_traintest = url_add_to_traintest.replace(escape("!!!!!"),roi_name)
        url_add_to_traintest = url_add_to_traintest.replace(escape("#####"),dataset)

        xhr_add_to_traintest.open('PUT', url_add_to_traintest , true);
        xhr_add_to_traintest.onload = function(){};
        xhr_add_to_traintest.send();

        // Update statistics
        let totalPatches = parseInt(document.getElementById("patches").textContent);
        let trainingPatches = parseInt(document.getElementById("training_patches").textContent);

        // number of patches annotated
        projROIs += 1;
        totalPatches += 1;
        document.getElementById('patches').innerHTML = totalPatches;

        // Number of patches in training set
        if (dataset == 'train') {
            projTrainingROIs += 1;
            trainingPatches += 1;
            document.getElementById('training_patches').innerHTML = trainingPatches;
        }

        //update the number of annotated objects by querying from the database
        updateObjectsAnnotated()

        function updateObjectsAnnotated() {
            let table_name = 'image';
            let col_name = 'id';
            let operation = '==';
            let value = "{{ image.id }}";
            let nObjects = getDatabaseQueryResults(table_name, col_name, operation, value).data.objects[0].nobjects;
            document.getElementById("annotated_objects").innerHTML = nObjects;
        }

        updatePercentCompleted();

        // if 3, 6, 12, 24... ROIs have been annotated and added to training set, train the first model
        let total_tmp = projROIs;
        let trainings_tmp = projTrainingROIs;
        if (trainings_tmp != 0 && trainings_tmp % 3 == 0){
            if (total_tmp > trainings_tmp){
                // check if (trainings_tmp/3) is a power of 2
                tr = trainings_tmp / 3;
                if ((tr & (tr - 1)) === 0){
                    xhr = new XMLHttpRequest();

                    url = "{{ url_for('api.retrain_dl', project_name=project.name)}}"
                    xhr.open("GET", url, true);

                    //Send the proper header information along with the request
                    xhr.setRequestHeader("Content-type", 'application/json; charset=utf-8');

                    xhr.onload = function() {
                        showDLReadyModal();
                    };
                    xhr.send();
                }
            }
        }
    }

    // upload the roi patch:
    uploadCanvasImage(
        "{{ url_for('api.post_roimask', project_name=project.name, image_name=image.name)}}",
        "roimask", canvas_roi, fd, uploadCallback);

    alreadyMakingAnnotation = false;
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
function setEraser(Erasersize){
    eraser_size = Erasersize;
	mode = "eraser";
	ctx_cropped_mask.globalCompositeOperation="destination-out";

	// grey out the button
	clearGreyedOutButton();
	enableEraser();
	document.getElementById("btnEraser").style.backgroundColor = "#CCCCCC";
}

function enableEraser(){
    let new_cursor;

    // radius = 3
    if (eraser_size == "extrasmall"){
        new_cursor="url('/static/images/eraser_cursor_extrasmall.png') 3 3,auto";
    }
    // radius = 9
    if (eraser_size == "small"){
        new_cursor="url('/static/images/eraser_cursor_small.png') 12 12,auto";
    }
    // radius = 21
    if (eraser_size == "medium"){
        new_cursor = "url('/static/images/eraser_cursor_medium.png') 27 27,auto";
    }
    //radius = 40
    if (eraser_size == "large"){
        new_cursor = "url('/static/images/eraser_cursor_large.png') 52 52,auto";
    }
    // Change to cursor erasor on the annotation tool ONLY here
    document.getElementById("canvas_cropped_mask").style.cursor = new_cursor;
}

function restoreCursor(){
    let new_cursor;
    new_cursor = 'crosshair';
    canvases = document.getElementsByTagName('canvas');
    for(let i = 0; i < canvases.length; i++) {
      canvases[i].style.cursor = new_cursor;
    }
    new_cursor = 'pointer';
    list_items = document.getElementsByTagName('li');
    for(let i = 0; i < list_items.length; i++) {
      list_items[i].style.cursor = new_cursor;
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// https://stackoverflow.com/a/38977789
// line intercept math by Paul Bourke http://paulbourke.net/geometry/pointlineplane/
// Determine the intersection point of two line segments
// Return FALSE if the lines don't intersect
function getLinesIntersection(x1, y1, x2, y2, x3, y3, x4, y4) {
    // Check if none of the lines are of length 0
	if ((x1 === x2 && y1 === y2) || (x3 === x4 && y3 === y4)) {
		return false
	}
	denominator = ((y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1))
    // Lines are parallel
	if (denominator === 0) {
		return false
	}
	let ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denominator
	let ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denominator
    // is the intersection along the segments
	if (ua < 0 || ua > 1 || ub < 0 || ub > 1) {
		return false
	}
    // Return a object with the x and y coordinates of the intersection
	const x = x1 + ua * (x2 - x1)
	const y = y1 + ua * (y2 - y1)
	return {x, y}
}

// output the point that would intersect a line and a side of the annotator window
function getIntersectionWithAnnotator(x1, y1, x2, y2) {
    const sides = ['top', 'right', 'bottom', 'left'];
    for (const side of sides) {
        const intersection = getIntersectionWithAnnotatorSide(x1, y1, x2, y2, side);
        if (intersection) return intersection;
    }
}

function getIntersectionWithAnnotatorSide(x1, y1, x2, y2, which_side) {
    let x3, y3, x4, y4;
    switch (which_side) {
        case 'top' :
            // top left corner:
            x3 = 0;
            y3 = 0;
            // top right corner:
            x4 = annotatorSize;
            y4 = 0;
            break;
        case 'right' :
            // top right corner:
            x3 = annotatorSize;
            y3 = 0;
            // bottom right corner:
            x4 = annotatorSize;
            y4 = annotatorSize;
            break;
        case 'bottom' :
            // bottom right corner:
            x3 = annotatorSize;
            y3 = annotatorSize;
            // bottom left corner:
            x4 = 0;
            y4 = annotatorSize;
            break;
        case 'left' :
            // bottom left corner:
            x3 = 0;
            y3 = annotatorSize;
            // top left corner:
            x4 = 0;
            y4 = 0;
            break;
        default:
            alert('Unknown side: ' + which_side);
            return;
    };
    return getLinesIntersection(x1, y1, x2, y2, x3, y3, x4, y4);
}
function getSquaredDistance(x1, y1, x2, y2) {
    return Math.pow(Math.abs(x2-x1), 2) + Math.pow(Math.abs(y2-y1), 2);
}

function prepareToolMouseListeners(which_canvas){

    if (!added_window_mouse_listeners) {
        added_window_mouse_listeners = true; // only fire this once

        window.addEventListener('mousemove', function(event) {
            if (event.button != 0) return; // Make sure it is left clicked
            if (annotatorEnabled && mousePressed && mode == 'freehand') {
                x = event.clientX - cropped_canvas_left_offset;
                y = event.clientY - cropped_canvas_top_offset;
                annotateData.push({"x": x, "y": y});
                fillRegion(alsoStroke=true);
                if (outside_annotation_canvas) {
                    const x1 = x;
                    const y1 = y;
                    const x2 = annotateData[0].x;
                    const y2 = annotateData[0].y;
                    const intersection = getIntersectionWithAnnotator(x1, y1, x2, y2);
                    const drawing_radius = 10;
                    const context = ctx_cropped_mask;
                    context.beginPath();
                    context.arc(intersection.x, intersection.y, drawing_radius, 0, 2 * Math.PI);
                    context.strokeStyle = 'white';
                    context.stroke();
                }
            }
        });

        window.addEventListener('mouseup', function(event) {
            if (!annotatorEnabled) return;
            if (event.button != 0) return; // Make sure it is left clicked
            bgImageEnabler = true;
            if (mousePressed) {
                mousePressed = false;
                if (mode == "freehand") {
                    fillRegion(alsoStroke=false);
                }
                else if (mode == "flood") {
                    floodFill();
                }
                resetCroppedMaskAlpha();
                annotateData = [];
                lastX = 0;
                lastY = 0;
                saveAnnotationHistory();
//                addNotification('Annotation history updated.');
            }
        });
    }

    which_canvas.addEventListener('mousedown', function(event) {
        if (!canAnnotate()) return;

        if (event.button == 2) { // right button
            // we dont want to painting superpixels when moving mouse whe right clicking#}
            mousePressed = false;

            // first check if the superpixels are ready
            if (!superpixels_boundary_load) {
                addNotification("Superpixel's boundary is not ready yet.");
            }

            if (!show_superpixel_boundary) {
                // draw superpixel boundary
                ctx_cropped_bg.clearRect(0, 0, annotatorSize, annotatorSize);
                ctx_cropped_bg.drawImage(canvas_bg_ori, leftUpperx_ori, leftUppery_ori, cropSize, cropSize, 0, 0, annotatorSize, annotatorSize);
                ctx_cropped_bg.globalAlpha = 0.3;
                ctx_cropped_bg.drawImage(canvas_superpixel_boundary_ori, leftUpperx_ori, leftUppery_ori, cropSize, cropSize, 0, 0, annotatorSize, annotatorSize);
                show_superpixel_boundary = true;
            } else {
                ctx_cropped_bg.clearRect(0, 0, annotatorSize, annotatorSize);
                ctx_cropped_bg.globalAlpha = 1;
                ctx_cropped_bg.drawImage(canvas_bg_ori, leftUpperx_ori, leftUppery_ori, cropSize, cropSize, 0, 0, annotatorSize, annotatorSize);
                show_superpixel_boundary = false;
            }
        }

        if (event.button != 0) return; // Make sure it is left clicked

        // annotatorEnabled = true;
        bgImageEnabler = false;

        pre_freehand_data = ctx_cropped_mask.getImageData(0, 0, annotatorSize, annotatorSize);

        cropped_canvas_left_offset = document.getElementById("annotator").offsetLeft + document.getElementById("cropped_canvas").offsetLeft;
        cropped_canvas_top_offset = document.getElementById("annotator").offsetTop + document.getElementById("cropped_canvas").offsetTop;
        mousePressed = true;
        alreadyMakingAnnotation = true;
        x = event.clientX - cropped_canvas_left_offset;
        y = event.clientY - cropped_canvas_top_offset;
        if (mode == 'superpixel') {
            paintSuperpixel(x, y);
        } else {
            annotateData.push({'x': x, 'y': y});
            if (mode == 'eraser') eraseSpot(x, y);
        }
    });

    which_canvas.addEventListener('mousemove', function(event) {
        if (event.button != 0) return; // Make sure it is left clicked
        if (annotatorEnabled && mousePressed) {
            const x = event.clientX - cropped_canvas_left_offset;
            const y = event.clientY - cropped_canvas_top_offset;
            if (mode == 'superpixel') {
                paintSuperpixel(x, y);
            }
            else if (mode == 'eraser') {
                annotateData.push({'x': x, 'y': y});
                eraseSpot(x, y);
            }
        }
    });

    which_canvas.addEventListener('mouseup', function(){
        annotatorEnabled = true;
    });
    which_canvas.addEventListener('mouseout', function() {
        outside_annotation_canvas = true;
    });
    which_canvas.addEventListener('mouseenter', function() {
        outside_annotation_canvas = false;
    });
    which_canvas.addEventListener('contextmenu', function(event) {
        event.preventDefault();
    });

}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// From a given starting point, flood-fill all the same-colored pixels around it with rgb
// (based on https://jamesonyu.wordpress.com/2015/05/01/flood-fill-algorithm-javascript/)
function floodFillInternal(context, start_x, start_y, fillR, fillG, fillB) {

    const h = annotatorSize;
    const w = annotatorSize;
    const drawingBoundTop = 0;
    let colorLayer = context.getImageData(0, 0, w, h);
    const startPos = (start_y*w + start_x)*4
    const startR = colorLayer.data[startPos+0];
    const startG = colorLayer.data[startPos+1];
    const startB = colorLayer.data[startPos+2];

    // if the start and destination are the same color, no need to run this function
    if (startR == fillR && startB == fillB && startG == fillG) return;

    function matchStartColor(pixelPos) {
        var r = colorLayer.data[pixelPos+0];
        var g = colorLayer.data[pixelPos+1];
        var b = colorLayer.data[pixelPos+2];
        return (r == startR && g == startG && b == startB);
    }

    function colorPixel(pixelPos) {
        colorLayer.data[pixelPos+0] = fillR;
        colorLayer.data[pixelPos+1] = fillG;
        colorLayer.data[pixelPos+2] = fillB;
        colorLayer.data[pixelPos+3] = 255;
    }

    let pixelStack = [[start_x, start_y]];
    while(pixelStack.length) {
        var newPos, x, y, pixelPos, reachLeft, reachRight;
        newPos = pixelStack.pop();
        x = newPos[0];
        y = newPos[1];

        pixelPos = (y*w + x) * 4;
        while(y-- >= drawingBoundTop && matchStartColor(pixelPos)) {
            pixelPos -= w * 4;
        }
        pixelPos += w * 4;
        ++y;
        reachLeft = false;
        reachRight = false;
        while(y++ < h-1 && matchStartColor(pixelPos)) {
            colorPixel(pixelPos);
            if(x > 0) {
                if(matchStartColor(pixelPos - 4)) {
                    if(!reachLeft) {
                        pixelStack.push([x - 1, y]);
                        reachLeft = true;
                    }
                }
                else if(reachLeft) {
                    reachLeft = false;
                }
            }
            if(x < w-1) {
                if(matchStartColor(pixelPos + 4)) {
                    if(!reachRight) {
                        pixelStack.push([x + 1, y]);
                        reachRight = true;
                    }
                }
                else if(reachRight) {
                    reachRight = false;
                }
            }
            pixelPos += w * 4;
        }
    }
    context.putImageData(colorLayer, 0, 0);
}

// flood-fill the annotation cropped mask with the current annotation class
function floodFill() {
    const color = getCurrentAnnotationRGB();
    floodFillInternal(ctx_cropped_mask,
        annotateData[0].x, annotateData[0].y,
        color[0], color[1], color[2]);
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// Fill the annotated object (and optionally stroke the boundary)
function fillRegion(alsoStroke = false){

    // If the annotation length is not zero, it is considered true
    if (!annotateData.length) return;

    // off-screen canvas
    let offscreen_canvas = document.createElement("canvas");
    const h = canvas_cropped_mask.height;
    const w = canvas_cropped_mask.width;
    offscreen_canvas.height = h;
    offscreen_canvas.width = w;
    let offscreen_context = offscreen_canvas.getContext("2d");

    // we start with a dummy color that will definitely not be annotated
    // so that we can clearly know which part of the image was annotated
    // (this way, we can remove the transparency from that part to avoid edge effects)
    const dummy_r = 27;
    const dummy_g = 32;
    const dummy_b = 87;
    offscreen_context.fillStyle = rgbToHex([dummy_r, dummy_g, dummy_b]);
    offscreen_context.fillRect(0,0,w,h);

    // fill the off-screen canvas with the polygon
    const expected_hex = ctx_cropped_mask.fillStyle;
    const expected_rgb = hexToRGB(expected_hex);
    offscreen_context.fillStyle = expected_hex;
    offscreen_context.beginPath();

    function createPath(context) {
        context.beginPath();
        context.moveTo(annotateData[0].x, annotateData[0].y);
        for (let i = 1; i < annotateData.length; i++) {
            context.lineTo(annotateData[i].x, annotateData[i].y);
        }
        context.closePath();
    }

    createPath(offscreen_context);
    offscreen_context.fill();

    // remove all transparency
    // (this is important for removing edge artifacts)
    let offscreen_image = offscreen_context.getImageData(0,0,w,h);
    let offscreen_data = offscreen_image.data;
    for (let i = 0; i < offscreen_data.length; i += 4) {
        const offscreen_r = offscreen_data[i+0];
        const offscreen_g = offscreen_data[i+1];
        const offscreen_b = offscreen_data[i+2];

        const is_dummy_color = offscreen_r == dummy_r && offscreen_g == dummy_g && offscreen_b == dummy_b;
        const is_fill_color = offscreen_r == expected_rgb.r && offscreen_g == expected_rgb.g && offscreen_b == expected_rgb.b;

        if (is_dummy_color || !is_fill_color) {
            offscreen_data[i+3] = 0; // <-- transparent
        }
        else {
            offscreen_data[i+3] = 255; // <!-- opaque
        }
    }
    offscreen_context.putImageData(offscreen_image, 0, 0);

    // removed the stroked selection from the main context
    ctx_cropped_mask.globalCompositeOperation = 'copy';
    ctx_cropped_mask.putImageData(pre_freehand_data, 0, 0);

    // port over the new region to the main context
    ctx_cropped_mask.globalCompositeOperation = 'source-over';
    ctx_cropped_mask.drawImage(offscreen_context.canvas, 0, 0);

    // fix transparency
    resetCroppedMaskAlpha();

    // optionally stroke the outline of the polygon
    if (alsoStroke) {

        // display a line around the outline:
        createPath(ctx_cropped_mask);
        ctx_cropped_mask.strokeStyle='black';
        ctx_cropped_mask.lineWidth=2;
        ctx_cropped_mask.stroke();

        // display a circle at the starting point:
        ctx_cropped_mask.arc(annotateData[0].x, annotateData[0].y, 5, 0, 2 * Math.PI);
        ctx_cropped_mask.stroke();
    }

}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// Fill the selected superpixel
function paintSuperpixel(curX, curY){

    // first check if the superpixels are ready
    if (!superpixels_loaded) {
        mousePressed = false;
        annotatorEnabled = true;
        addNotification('Superpixels Warning: Superpixels are not ready yet.');
        return;
    }

    let s = null;
    let path = [];
    path.push({ "x" : curX, "y" :curY });
    let cropped_mask_data = ctx_cropped_mask.getImageData(0, 0, annotatorSize, annotatorSize);
    let actual_x = Math.round(curX / (annotatorSize / cropSize));
    let actual_y = Math.round(curY / (annotatorSize / cropSize));
    let index = (cropSize * actual_y + actual_x) * 4;
    //alert(curX + " || " + curY + " || " + actual_x + " || " + actual_y + " || " + index);

    let r = superpixel_data.data[index+0];
    let g = superpixel_data.data[index+1];
    let b = superpixel_data.data[index+2];
    let red, green, blue;

    const color_to_paint = getCurrentAnnotationRGB();

    //alert(r + " || " + g + " || " + b);

    let annotated_indices = new Set();

    while (path.length > 0){
		s = path.pop();

		if (s == null) break;

		actual_x = Math.round(s.x / (annotatorSize / cropSize));
		actual_y = Math.round(s.y / (annotatorSize / cropSize));
		index = (cropSize * actual_y + actual_x) * 4;
		//alert(s.x + " || " + s.y + " || " + actual_x + " || " + actual_y + " || " + index);
		red = superpixel_data.data[index+0];
		green = superpixel_data.data[index+1];
		blue = superpixel_data.data[index+2];

		// Check if current pixel has been labeled
        const anno_index = (annotatorSize * s.y + s.x) * 4;
        if (annotated_indices.has(anno_index)) continue;

		// If current pixel is not in the desired superpixel, skip it
		if (red != r || green != g || blue != b) continue;

        annotated_indices.add(anno_index);

		// paint the pixel
		cropped_mask_data.data[anno_index+0] = color_to_paint[0];
		cropped_mask_data.data[anno_index+1] = color_to_paint[1];
		cropped_mask_data.data[anno_index+2] = color_to_paint[2];
		cropped_mask_data.data[anno_index+3] = 255; // <-- will be reset later

		// Expand from one point
		let top = null, left = null, right = null, bottom = null;
		if (s.x > 0)
		{
			left = { "x" : s.x - 1, "y" : s.y };
		}
		if (s.y > 0)
		{
			top = { "x" : s.x, "y" : s.y - 1 };
		}
		if (s.x < annotatorSize)
		{
			right = { "x" : s.x + 1, "y" : s.y };
		}
		if (s.y < annotatorSize)
		{
			bottom = { "x" : s.x, "y" : s.y + 1 };
		}

		// Track the trace
		if (left) path.push(left);
		if (top) path.push(top);
		if (right) path.push(right);
		if (bottom) path.push(bottom);
	}

	// Update canvas
    setCroppedMaskData(cropped_mask_data);

} // paintSuperpixel
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
// Functions for setting the different annotation modes:
function clearGreyedOutButton(){
    restoreCursor();
	document.getElementById("btnFreehand").style.backgroundColor = "#FFFFFF";
	document.getElementById("btnSuperPixel").style.backgroundColor = "#FFFFFF";
	document.getElementById("btnRemove").style.backgroundColor = "#FFFFFF";
	document.getElementById("btnEraser").style.backgroundColor = "#FFFFFF";
}

// set the mode to flood from the current point
function setFlood(){
	mode = "flood";
	ctx_cropped_mask.globalCompositeOperation="copy";

	clearGreyedOutButton();
	document.getElementById("btnRemove").style.backgroundColor = "#CCCCCC";
}

function setFreeHand(){
	mode = "freehand";
	ctx_cropped_mask.globalCompositeOperation="source-over";

	clearGreyedOutButton();
	document.getElementById("btnFreehand").style.backgroundColor = "#CCCCCC";

	ctx_cropped_mask.lineWidth = 5;
}

function setSuperPixel(){
    mode = "superpixel";

	clearGreyedOutButton();
	document.getElementById("btnSuperPixel").style.backgroundColor = "#CCCCCC";
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// Draw the contour of the object
function eraseSpot(x, y) {
    switch (eraser_size) {
        case "extrasmall": radius=3; break;
        case "small": radius=12; break;
        case "medium": radius=27; break;
        case "large": radius=52; break;
        default: alert('Error: Unknown eraser size.');
    }

    ctx_cropped_mask.beginPath();
    ctx_cropped_mask.arc(x, y, radius, 0, Math.PI * 2);
    ctx_cropped_mask.fill();
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
function clearArea() {
    alreadyMakingAnnotation = false;
    ctx_cropped_mask.setTransform(1, 0, 0, 1, 0, 0);
    ctx_cropped_mask.clearRect(0, 0, annotatorSize, annotatorSize);
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
// Replace all black pixels in a context with a given color
function replaceBlackInternal(context, w, h, replaceR, replaceG, replaceB) {
    let image_data = context.getImageData(0, 0, w, h);
    let data = image_data.data;
	for (let i = 0; i < data.length; i += 4) {
	    if (!data[i+0] && !data[i+1] && !data[i+2]) {
	        data[i+0]=replaceR;
	        data[i+1]=replaceG;
	        data[i+2]=replaceB;
	        data[i+3]=255;
	    }
    }
    context.putImageData(image_data, 0, 0);
}

// Replace all black pixels in the annotation mask with a given color
function replaceMaskBlack(rgb) {
    const w = annotatorSize;
    const h = annotatorSize;
    replaceBlackInternal(ctx_cropped_mask, w, h, rgb[0], rgb[1], rgb[2]);
    resetCroppedMaskAlpha();
    saveAnnotationHistory();
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// Assign some image data to the cropped and recalculate the alpha channel
function setCroppedMaskData(new_image_data) {
    ctx_cropped_mask.putImageData(new_image_data, 0, 0);
    resetCroppedMaskAlpha();
}
////////////////////////////////////////////////////////////////////////////////////////////////////

////////////////////////////////////////////////////////////////////////////////////////////////////
// update the disability of the buttons on the annotation tool
function enableToolButton(){

    let assignedBoolean;
    switch(layer) {
        case "annotation":
        case "fuse":
            assignedBoolean = false;
            break;

        case "origin":
        case "prediction":
            assignedBoolean = true;
            break;
        default:
            break;
    }
    document.getElementById("btnFreehand").disabled = assignedBoolean;
    document.getElementById("btnSuperPixel").disabled = assignedBoolean;
    document.getElementById("btnRemove").disabled = assignedBoolean;
    document.getElementById("btnEraser").disabled = assignedBoolean;
    document.getElementById("btnEraser_extrasmall").disabled = assignedBoolean;
    document.getElementById("btnEraser_small").disabled = assignedBoolean;
    document.getElementById("btnEraser_medium").disabled = assignedBoolean;
    document.getElementById("btnEraser_large").disabled = assignedBoolean;
    document.getElementById("btnImport").disabled = (assignedBoolean||!prediction_loaded);
    document.getElementById("btnUpload").disabled = assignedBoolean;
    document.getElementById("btnPositive").disabled = assignedBoolean;
    document.getElementById("btnNegative").disabled = assignedBoolean;
    document.getElementById("btnUnknown").disabled = assignedBoolean;
    document.getElementById("btnClear").disabled = assignedBoolean;
    document.getElementById("btnRedo").disabled = assignedBoolean;
    document.getElementById("btnUndo").disabled = assignedBoolean;
}
////////////////////////////////////////////////////////////////////////////////////////////////////