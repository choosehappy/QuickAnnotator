


////////////////////////////////////////////////////////////////////////////////////////////////////
window.onscroll = function() {setScroll()};

var updateCropSize = function() {
  cropSize = Math.pow(2, cropsize_slider.value);
	cropsize_value.innerHTML = cropSize;
	//Update Cookie with expiring after 1 day
	setCookie("UserCropSize",cropSize.toString(),1)
}

cropsize_slider.oninput = updateCropSize;
zoom_factor_slider.oninput = updateZoomFactor;
annotator_size_slider.oninput = updateAnnotatorSize;
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
var zoomKeyEvent = function(event) {
    if (event.ctrlKey) {
        console.log(event.key);
        if (event.key == '=' || event.key == '+') {
            event.preventDefault();
            zoomIn();
        }
        else if (event.key == '-' || event.key == '_' && event.shiftKey) {
            event.preventDefault();
            zoomOut();
        }
    }
};
var zoomWheelEvent = function(event) {
    if (event.ctrlKey) {
        const scrollUp = event.deltaY < 0;
        const scrollDown = event.deltaY > 0;
        if (scrollUp) {
            event.preventDefault();
            zoomIn();
        }
        else if (scrollDown) {
            event.preventDefault();
            zoomOut();
        }
    }
};
document.addEventListener("keydown", zoomKeyEvent, {passive: false});
document.addEventListener("wheel", zoomWheelEvent, {passive: false});
document.addEventListener("DOMMouseScroll", zoomWheelEvent, {passive: false});
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
function Point(x, y){
    this.x = x;
    this.y = y;
}
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
class ActiveList{ // element type: GraphNode
    constructor() {
        this.head = null;
        this.size = 0;
    }

    isEmpty(){
        return this.size == 0;
    }

    remove(p){
        if(this.size == 0) return this;

        if(this.head.x == p.x && this.head.y == p.y){
            this.head = this.head.next;
            this.size--;
            return this;
        }

        let current = this.head;
        while(current.next != null){
            if(current.next.x == p.x && current.next.y == p.y){
                current.next = current.next.next;
                this.size--;
                return this;
            }
            current = current.next;
        }
        return this;
    }

    add(p){
        if (this.head == null){
            this.head = p;
            this.size++;
            return this;
        }
        let current = this.head;
        while(current.next != null){
            if (p.global_cost < current.next.global_cost){
                p.next = current.next;
                current.next = p;
                this.size++;
                return this;
            }
            current = current.next;
        }
        current.next = p;
        this.size++;
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
// make our floating panels draggable
$(function() {
    $( "#toolbox" ).draggable({
        drag: function(){
            $("#cropped_canvas").css('left', $(this).position().left);
            $("#cropped_canvas").css('top', $(this).position().top);
        }
    });
    $( "#info" ).draggable({
        drag: function(){}
    });
});
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
/**
 * Load existing job timers for the project and image specific jobs.
 */
function loadRunningJobTimers() {

    // the project jobs
    const project_id = {{ project.id }};
    loadRunningJobsForProject(project_id);

    // (superpixels & predictions are loaded when the image loads in init)

    // retraining (this is not image-specific)
    const command = 'retrain_dl';
    const callback = reloadPrediction;
    // (placeholder for how to potentially use image_id for other jobs)
    // const image_id = {{ image.id }};
    const image_id = null;
    let indicationTarget = 'model'

    startJobCheckerIfExists(project_id, image_id, command, callback, indicationTarget);
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function resetAnnotatorSize() {
    const annotation_canvases = document.getElementsByClassName("annotator");
    for (let i = 0; i < annotation_canvases.length; i++) {
        annotation_canvases.item(i).height = annotatorSize;
        annotation_canvases.item(i).width = annotatorSize;
    }
    disableSmoothing()
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function disableSmoothing() {
    // imageSmoothingEnabled property need to be set again after each canvas resizing
    ctx_mask.imageSmoothingEnabled = false;
    ctx_cropped_mask.imageSmoothingEnabled = false;
    ctx_cropped_result.imageSmoothingEnabled = false;
    ctx_bg_ori.imageSmoothingEnabled = false;
    ctx_mask_ori.imageSmoothingEnabled = false;
    ctx_result_ori.imageSmoothingEnabled = false;
    ctx_superpixel_boundary_ori.imageSmoothingEnabled = false;
}
////////////////////////////////////////////////////////////////////////////////////////////////////


////////////////////////////////////////////////////////////////////////////////////////////////////
function init() {

    // load up timers for existing jobs
    loadRunningJobTimers();

    // set the annotation tool canvas sizes
    resetAnnotatorSize();

    // Register an event listener to call the resizeCanvas() function each time the window is resized
    //window.addEventListener('resize', resizeCanvas, false);
    // Draw canvas border for the first time
    //resizeCanvas();
    let img = new Image();

    img.onload = function () {
        imgHeight = img.height;
        imgWidth = img.width;

        let canvasDivWidth = document.getElementById('canvas').offsetWidth;
        canvasWidth_ori = canvasDivWidth * (1 - 0.01 * 2);
        canvasHeight_ori = canvasWidth_ori * imgHeight / imgWidth;

        canvas_bg_ori.width = imgWidth;
        canvas_bg_ori.height = imgHeight;

        canvas_mask_ori.width = imgWidth;
        canvas_mask_ori.height = imgHeight;

        canvas_superpixel_ori.width = imgWidth;
        canvas_superpixel_ori.height = imgHeight;

        canvas_superpixel_boundary_ori.width = imgWidth;
        canvas_superpixel_boundary_ori.height = imgHeight;

        canvas_result_ori.width = imgWidth;
        canvas_result_ori.height = imgHeight;

        ctx_bg.drawImage(img, 0, 0, canvasWidth_ori, canvasHeight_ori);
        ctx_bg_ori.drawImage(img, 0, 0);

        resetZoom();
        resetPanels();

        document.getElementById("dim").innerHTML = imgWidth.toString().concat(" x ", imgHeight.toString());

        // the url's of the images to load upon initialization:
        let mask_url = "{{ url_for('api.get_mask', project_name=project.name, image_name=image.name)}}";
        let superpixel_url = "{{ url_for('api.get_superpixels', project_name=project.name, image_name=image.name)}}";
        let superpixel_boundary_url = "{{ url_for('api.get_superpixels_boundary', project_name=project.name, image_name=image.name)}}";

        // when the annotation mask is loaded, draw the mask:
        let drawMask = function () {
            redrawMask();
            updatePercentCompleted();
        }

        // when the superpixels are generated, this function will draw the superpixels:
        let drawSuperpixels = function () {

            // only show the Superpixels ready when superpixel is ready and boundary is nto ready, user only need one message
            if (superpixels_loaded && !superpixels_boundary_load) {
                addNotification('Superpixels loaded: Superpixels Ready')
            }

            // tell the cropped tool that the superpixels are ready
            superpixels_loaded = true;

            // we must redraw the region to update the stale superpixel data:
            redrawCroppedTool(canvas_mask_ori, false);
            // TODO:Keep for now, do we want to switch to SP mode when SP ready
            // setSuperPixel();

            // Once the superpixels are drawn, try to generate and load the boundary
            loadImageAndRetry(superpixel_boundary_url, ctx_superpixel_boundary_ori, drawSuperpixelsBoundary);

        }; // drawSuperpixels

        // when the superpixels are generated, this function will draw the superpixels:
        let drawSuperpixelsBoundary = function () {

            addNotification("Superpixels and Boundary loaded. Right click on the annotation tool to see the boundary.", "Superpixels and Boundary Ready")

            // tell the cropped tool that the boundary of superpixels are ready
            superpixels_boundary_load = true;

            // we must redraw the region to update the stale superpixel boundary data:
            redrawCroppedTool(canvas_mask_ori, false);
            // TODO:Keep for now, do we want to switch to SP mode when SP ready
            // setSuperPixel();

        }; // drawSuperpixels boundary

        // load the images from the server:
        loadImageAndRetry(mask_url, ctx_mask_ori, drawMask, true/*ignore error*/);
        loadImageAndRetry(superpixel_url, ctx_superpixel_ori, drawSuperpixels, false, 'superpixel');

        // load any prediction:
        reloadPrediction();

        // now automatically start annotating a patch
        startX = getUrlParameter('startX');
        startY = getUrlParameter('startY');
        if (startX === '' || startY === '') {
            //Relocate the selection rectangle to the center of the image
            cropped_center_x = 0.5 * canvas_bg.width;
            cropped_center_y = 0.5 * canvas_bg.height;
            restoreSelection();
        } else {
            //  start annotating at that rectangle supplied by the url

            // this is from line 50 of make_embed.py but should really be set programmatically in the future
            patchSize = getUrlParameter('cropSize');

            // update the slider
            cropsize_slider.value = Math.log2(patchSize);
            updateCropSize();

            // turn the starting locations into the centroid since that's
            // what showRect requires:
            cropped_center_x = Number(startX) + cropSize / 2;
            cropped_center_y = Number(startY) + cropSize / 2;

            // the patch size was on the original image size (i.e. canvas_bg_ori)
            // while the canvas rendered in html has size of canvasWidth and canvasHeight,
            // so we must scale our patch size appropriately
            cropped_center_x *= canvasWidth / canvas_bg_ori.width;
            cropped_center_y *= canvasHeight / canvas_bg_ori.height;

            restoreSelection();

        }

        // prepare for annotating
        redrawCroppedTool();

        // must re-disable smoothing every resize
        disableSmoothing()

        // start with the annotation image
        showAnnotation();
        document.getElementById('Annotation-dot').style.backgroundColor = colorON;

    }; // image loaded

    img.src = "{{ url_for('api.get_image', project_name=project.name, image_name=image.name)}}";

    // Make the annotation canvas draggable

    // listen on the selected canvas layers for mouse actions:
    prepareMouseListeners(canvas_bg);
    prepareMouseListeners(canvas_mask);
    prepareMouseListeners(canvas_result);
    prepareToolMouseListeners(canvas_cropped_mask);
    //2/4 added
    prepareToolMouseListeners(canvas_cropped_bg);
    prepareToolMouseListeners(canvas_cropped_result);

    // add global listener since user may release mouse on non-canvas area since we have zoom factor
    prepareGlobalListeners(document);

    // Set parameters
    ctx_cropped_mask.lineWidth = 5;
    cropped_canvas_left_offset = canvas_cropped_mask.offsetLeft;
    cropped_canvas_top_offset = canvas_cropped_mask.offsetTop;

    //Update the cropSize here
    if (getCookie("UserCropSize") != "") {
        cropSize = getCookie("UserCropSize")
        cropsize_slider.value = Math.log2(cropSize);
    } else {
        // "{{defaultCropSize}}" is a rendered variable see 'rendered_project_image' in QA_html.py
        defaultCropSize = Number("{{defaultCropSize}}");
        // Set default crop size
        cropsize_slider.value = Math.log2(defaultCropSize);
    }
    updateCropSize();

    // Set to freehand mode until superpixels are ready
    setToPositive();
    setFreeHand();

    // restore the cursors
    restoreCursor();

    //Need to assign an initial value to toggle the image information window
    showOrHideImageInformation( 'visible');

    if ('{{project.iteration}}' == '-1') {
        updateTrafficLight('model',colorNOTAVAILABLE)
    } else {updateTrafficLight('model',colorAVAILABLE)}

} // init
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// key bindings:
shortcut.add("q", function() {
    annotationDotToggle();
});

shortcut.add("w", function() {
    predictionDotToggle();
});

shortcut.add("a", function() {
    setFreeHand();
});

shortcut.add("s", function() {
    setSuperPixel();
});

shortcut.add("d", function() {
    setFlood();
});

shortcut.add("f", function() {
    setEraser(eraser_size);
});

shortcut.add("g", function() {
    importPrediction();
});

shortcut.add("h", function() {
    prepareForUpload();
});

shortcut.add("z", function() {
    setToPositive();
});

shortcut.add("x", function() {
    setToNegative();
});

shortcut.add("c", function() {
    setToUnknown();
});

shortcut.add("v", function() {
    undo();
});

shortcut.add("b", function() {
    redo();
});

shortcut.add("n", function() {
    clearArea();
});

shortcut.add("i", function() {
    imageInformationToggle();
});
////////////////////////////////////////////////////////////////////////////////////////////////////



////////////////////////////////////////////////////////////////////////////////////////////////////
// window control tool here: including close drag etc
function showOrHideImageInformation(visibility) {
    document.getElementById('info').style.visibility = visibility;
    if (visibility == 'visible') {
         document.getElementById("Image-Information-dot").style.backgroundColor = colorON;
    } else if (visibility = 'hidden') {
         document.getElementById("Image-Information-dot").style.backgroundColor = colorOFF;
    }
}

// Toggle the window
function imageInformationToggle(){
    let e = document.getElementById('info');
    if(e.style.visibility == 'visible') {
         e.style.visibility = 'hidden';
         document.getElementById("Image-Information-dot").style.backgroundColor = colorOFF;
    } else if(e.style.visibility == 'hidden') {
         e.style.visibility = 'visible';
         document.getElementById("Image-Information-dot").style.backgroundColor = colorON;
    }
}
////////////////////////////////////////////////////////////////////////////////////////////////////

