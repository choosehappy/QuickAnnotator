// Declaration
/////////////////////////////////////////////////
let w, h, margin, radius;
let svg;
let cropSize;
let xScale, yScale;
let xAxis, yAxis;
let circleAttrs;
let preImgSize, marginSize;

var patchnumber_slider = document.getElementById("patchnumberSlider");
var patchnumber_value = document.getElementById("patchnumberValue");
var currentModelId_value = document.getElementById("currentModelId");
let embed_modelID = document.getElementById("embedID");
let patchnumber = Math.pow(2, patchnumber_slider.value);
let viewEmbed_url = document.getElementById("viewEmbed_url").href;
var updatepatchnumber = function () {
    if (patchnumber_slider.value == patchnumber_slider.max) {
        patchnumber = "all"
    } else {
        patchnumber = Math.pow(2, patchnumber_slider.value);
    }

    patchnumber_value.innerHTML = patchnumber;
}
patchnumber_slider.oninput = updatepatchnumber;


// Initialization part
/////////////////////////////////////////////////////////////////
setCurrentIDNA()
reloadChartData()


//Below are functions directly related to the svg graphs
//////////////////////////////////////////////////////////
/**
 * The core function in the embed-main.js
 * It loads a JSON format graphdata and append in form of svg
 * Note: loadData will append a new vector graph
 *       need remove the old one if we want only one
 */
function loadData(csvData) {

    // ToDO parse an broken random string and modify accordingly
    // check if graph data was provided (Issue #430)
    if (typeof csvData === 'undefined') {
        alert('{{error_message}}');
        addNotification('{{error_message}}');
        throw new Error('{{error_message}}');
        currentModelId_value.innerHTML = "N/A";
    }

    // Set dimensions for graph
    w = window.innerWidth;
    h = window.innerHeight;
    // Leave extra space for loading png image when hovering over the dot by setting extra margin
    preImgSize = 200;
    marginSize = 40;
    margin = {top: marginSize, right: preImgSize, bottom: preImgSize, left: marginSize};
    radius = 6;
    // Set dimensions for svg
    svg = d3.select("body").append("svg").attr({
        width: w-marginSize,
        // 60 is the size of the notification pane here
        height: h-marginSize-60,
    });

    // Parse the rawCSV data into graphdata by d3
    let graphData;
    graphData = d3.csv.parse(csvData, function (d) {
        // Convert data to the proper type using accessor
        return {
            "#filename": d["#filename"],
            "group": Number(d["group"]),
            "x": Number(d["x"]),
            "y": Number(d["y"]),
        };
    });

    // Define the ranges for the data
    xScale = d3.scale.linear()
        .domain([d3.min(graphData, function (d) {
            return d["x"] - 1
        }), d3.max(graphData, function (d) {
            return d["x"] + 1;
        })])
        .range([margin.left, w - margin.right]);  // Set margins for x specific
    yScale = d3.scale.linear()
        .domain([d3.min(graphData, function (d) {
            return d["y"] - 1
        }), d3.max(graphData, function (d) {
            return d["y"] + 1;
        })])
        .range([margin.top, h - margin.bottom]);  // Set margins for y specific

    // Add X and Y Axis (Note: orient means the direction that ticks go, not position)
    xAxis = d3.svg.axis().scale(xScale).orient("top");
    yAxis = d3.svg.axis().scale(yScale).orient("left");

    circleAttrs = {
        cx: function (d) {
            return xScale(d["x"]);
        },
        cy: function (d) {
            return yScale(d["y"]);
        },
        fill: function (d) {
            return "#" + Math.floor((Math.abs(Math.sin(d["group"] + 1) * 16777215)) % 16777215).toString(16)
        }, // Generate random seeded hex color
        stroke: function (d) {
            if (d["#filename"].includes("roi")) {
                return "black";
            } else {
                return "";
            }
        },
        r: radius
    };

    // Adds X-Axis as a 'g' element
    svg.append("g").attr({
        "class": "axis",  // Give class so we can style it
        transform: "translate(" + [0, margin.top] + ")"  // Translate just moves it down into position (or will be on top)
    }).call(xAxis);  // Call the xAxis function on the group

    // Adds Y-Axis as a 'g' element
    svg.append("g").attr({
        "class": "axis",
        transform: "translate(" + [margin.left, 0] + ")"
    }).call(yAxis);  // Call the yAxis function on the group

    svg.selectAll("circle")
        .data(graphData)
        .enter()
        .append("circle")
        .attr(circleAttrs)  // Get attributes from circleAttrs var
        .on("mouseover", handleMouseOver)
        .on("mouseout", handleMouseOut)
        .on("click", handleClick);
}

// Create Event Handlers for mouse
function handleMouseOver(d, i) {  // Add interactivity
    // Use D3 to select element, change size

    d3.select(this).attr({r: radius * 2});


    // Specify the image location
    let embedName = d["#filename"].replace(/^.*[\\\/]/, '');
    // Check whether this patch is generated by make_patches or human annotation
    let img_url
    if (embedName.includes("roi")) {
        img_url = new URL("{{ url_for('api.get_roi', project_name=project_name, roi_name='')}}" +
            embedName, window.location.origin)
    } else {
        img_url = new URL("{{ url_for('api.get_embed', project_name=project_name, image_name='')}}" +
            embedName, window.location.origin)
    }

    updatePatchCropSize(img_url);

    svg.append("image")
        .attr("id", "img" + parseInt(d["x"]) + "-" + parseInt(d["y"]) + "-" + i)
        .attr("xlink:href", img_url)
        .attr("x", function () {
            return xScale(d["x"]) + 20;
        })
        .attr("y", function () {
            return yScale(d["y"]) + 10;
        })
        .attr("width", preImgSize)
        .attr("height", preImgSize);

    // Specify where to put label of text
    svg.append("text")
        .attr({
            id: "t" + parseInt(d["x"]) + "-" + parseInt(d["y"]) + "-" + i,  // Create an id for text so we can select it later for removing on mouseout
            x: function () {
                return xScale(d["x"]) + 20;
            },
            y: function () {
                return yScale(d["y"]);
            }
        })
        .text(embedName) // Value of the text
        .style("font-size", "16px");
}

function handleMouseOut(d, i) {
    // Use D3 to select element, change color back to normal
    d3.select(this).attr({r: radius});

    // Select image by id and then remove
    d3.select("#img" + parseInt(d["x"]) + "-" + parseInt(d["y"]) + "-" + i).remove(); // Remove the image

    // Select text by id and then remove
    d3.select("#t" + parseInt(d["x"]) + "-" + parseInt(d["y"]) + "-" + i).remove();  // Remove text location
}

function handleClick(d, i) {
    let embedName = d["#filename"].split('/').pop(); // Extract file name
    let fileName = embedName.replace(/\.[^/.]+$/, ""); // Remove file extension
    //var pieces = fileName.split("_");
    //var yCoord = parseInt(pieces.pop());
    //var xCoord = parseInt(pieces.pop());


    // Need to deal with two patches
    // roi cases & patches case
    // It is "\" here, because it is the file name not url
    fileName = fileName.replace("_roi", "").replace("roi\\", "").replace("patches\\", "")


    // get y coordinate
    let idx = fileName.lastIndexOf("_");
    let yCoord = parseInt(fileName.substring(idx + 1));
    fileName = fileName.substring(0, idx);

    // get x coordinate
    idx = fileName.lastIndexOf("_");
    let xCoord = parseInt(fileName.substring(idx + 1));
    fileName = fileName.substring(0, idx);

    // we will load the annotation page for this image:
    let new_url = "/{{ project_name }}/" + fileName + ".png/annotation";

    new_url = new URL(new_url, window.location.origin)

    // and append the coordinates of the top-left corner of this patch and the cropsize of this patch:
    new_url.searchParams.append('startX', xCoord.toString())
    new_url.searchParams.append('startY', yCoord.toString())
    new_url.searchParams.append('cropSize', cropSize)

    // open the annotation page in a new window:
    window.open(new_url, '_blank');

} // handleClick
////////////////////////////////////////////////////////////////////////


// Below are function that are more related to features on the embed page
// View-reembed button related functions
function reloadChartData() {
    let run_url = new URL("{{ url_for('api.get_embed_csv',project_name=project_name) }}", window.location.origin);
    let embed_modelID_value = embed_modelID.value;
    run_url.searchParams.append("modelid", embed_modelID_value);

    let xhr_embedcsv = new XMLHttpRequest();
    xhr_embedcsv.open("GET", run_url, true);
    xhr_embedcsv.onload = function() {
        const status_code = xhr_embedcsv.status;
        switch(status_code) {
            case 200:
                removeChartData();
                loadData(xhr_embedcsv.response); //# send data here
                currentModelId_value.innerHTML = embed_modelID.value;
                addNotification("Current embedding project is '{{project_name}}', and current embedding model ID is " + embed_modelID.value.toString())
                break;
            case 400:
                let json_output = JSON.parse(xhr_embedcsv.responseText);
                showWindowMessage('ERROR 400: ' + json_output.error, 'HTML Error');
                break;
            default:
                showWindowMessage('ERROR ' + status_code + ': (Unknown error)', 'HTML Error');
        }
    };
    xhr_embedcsv.send();
}

function removeChartData(){
    d3.select("svg").remove();
}

function setCurrentIDNA(){
    currentModelId_value.innerHTML = "N/A";
}

//Get cropSize in the annotation page
function updatePatchCropSize(url) {
    let img = new Image();
    img.src = url;
    img.onload = function () {
        cropSize = this.width
    };

}

function make_embed() {
    addNotification("Re-embed process starts, please wait");
    addNotification("Please view the embed when the make_embed process is finished");
    let run_url = new URL("{{ url_for('api.make_embed', project_name=project_name) }}", window.location.origin);
    // Parse the # of patches
    let embed_modelID_value = embed_modelID.value;
    run_url.searchParams.append("modelid", embed_modelID_value);
    if (typeof (patchnumber) == "number") {
        run_url.searchParams.append("numimgs", patchnumber)
    }
    // Parse -1 when selecting all the patches See backend
    else {
        run_url.searchParams.append("numimgs", -1)
    }
    return loadObjectAndRetry(run_url, enableViewEmbed)
}

function enableViewEmbed() {
    document.getElementById("viewEmbed").disabled = false;
}